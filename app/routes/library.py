from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
import logging

from app import db
from app.models.library import Library, BookIssue
from app.models.student import Student
from app.utils.decorators import staff_required, admin_required
from app.utils.validators import validate_required_fields

# Create blueprint
library = Blueprint('library', __name__)
library_bp = library  # Alias for consistent naming

# Configure logging
logger = logging.getLogger(__name__)


@library.route('/books', methods=['GET'])
@jwt_required()
def get_books():
    """Get all books with optional search and filtering"""
    try:
        # Get query parameters
        search_query = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        available_only = request.args.get('available_only', 'false').lower() == 'true'
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Build query
        query = Library.query.filter_by(is_active=True)
        
        # Apply search filter
        if search_query:
            search_filter = (
                Library.title.contains(search_query) |
                Library.author.contains(search_query) |
                Library.isbn.contains(search_query)
            )
            query = query.filter(search_filter)
        
        # Apply category filter
        if category:
            query = query.filter_by(category=category)
        
        # Apply availability filter
        if available_only:
            query = query.filter(Library.available_copies > 0)
        
        # Order by title
        query = query.order_by(Library.title)
        
        # Paginate
        books = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'books': [book.to_dict() for book in books.items],
            'pagination': {
                'page': books.page,
                'pages': books.pages,
                'per_page': books.per_page,
                'total': books.total,
                'has_next': books.has_next,
                'has_prev': books.has_prev
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching books: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch books',
            'error': str(e)
        }), 500


@library.route('/books/<book_id>', methods=['GET'])
@jwt_required()
def get_book_details(book_id):
    """Get detailed information about a specific book"""
    try:
        book = Library.query.filter_by(book_id=book_id, is_active=True).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        # Get issue history for the book
        issue_history = BookIssue.query.filter_by(book_id=book_id)\
                                      .order_by(BookIssue.issue_date.desc())\
                                      .limit(10).all()
        
        book_data = book.to_dict()
        book_data['issue_history'] = [issue.to_dict() for issue in issue_history]
        
        return jsonify({
            'success': True,
            'book': book_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching book details: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch book details',
            'error': str(e)
        }), 500


@library.route('/books', methods=['POST'])
@staff_required
def add_book():
    """Add a new book to the library (Staff only)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'author', 'total_copies']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return validation_error
        
        # Check if ISBN already exists (if provided)
        if data.get('isbn'):
            existing_book = Library.query.filter_by(isbn=data['isbn']).first()
            if existing_book:
                return jsonify({
                    'success': False,
                    'message': 'Book with this ISBN already exists'
                }), 400
        
        # Generate book ID
        book_id = Library.generate_book_id()
        
        # Create new book
        book = Library(
            book_id=book_id,
            title=data['title'].strip(),
            author=data['author'].strip(),
            isbn=data.get('isbn', '').strip() or None,
            publisher=data.get('publisher', '').strip(),
            publication_year=data.get('publication_year'),
            category=data.get('category', '').strip(),
            total_copies=int(data['total_copies']),
            available_copies=int(data['total_copies']),
            shelf_location=data.get('shelf_location', '').strip(),
            condition=data.get('condition', 'Good')
        )
        
        db.session.add(book)
        db.session.commit()
        
        logger.info(f"New book added: {book_id} - {book.title}")
        
        return jsonify({
            'success': True,
            'message': 'Book added successfully',
            'book': book.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding book: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to add book',
            'error': str(e)
        }), 500


@library.route('/issue', methods=['POST'])
@staff_required
def issue_book():
    """Issue book to student (Staff only)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['book_id', 'student_id']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return validation_error
        
        book_id = data['book_id'].strip()
        student_id = data['student_id'].strip()
        
        # Check if book exists and is available
        book = Library.query.filter_by(book_id=book_id, is_active=True).first()
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        # Check if student exists
        student = Student.query.filter_by(roll_no=student_id).first()
        if not student:
            return jsonify({
                'success': False,
                'message': 'Student not found'
            }), 404
        
        # Check if student has too many books (limit: 5 books)
        active_issues = BookIssue.get_student_issues(student_id, active_only=True)
        if len(active_issues) >= 5:
            return jsonify({
                'success': False,
                'message': 'Student has reached maximum book limit (5 books)'
            }), 400
        
        # Check if student has overdue books
        overdue_books = [issue for issue in active_issues if issue.is_overdue]
        if overdue_books:
            return jsonify({
                'success': False,
                'message': 'Student has overdue books. Please return them first.',
                'overdue_books': [issue.to_dict() for issue in overdue_books]
            }), 400
        
        # Issue the book
        success, message = book.issue_book(student_id)
        
        if not success:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        logger.info(f"Book issued: {book_id} to {student_id}")
        
        return jsonify({
            'success': True,
            'message': message,
            'book': book.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error issuing book: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to issue book',
            'error': str(e)
        }), 500


@library.route('/return', methods=['POST'])
@staff_required
def return_book():
    """Return book from student (Staff only)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['book_id', 'student_id']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return validation_error
        
        book_id = data['book_id'].strip()
        student_id = data['student_id'].strip()
        damage_fee = data.get('damage_fee', 0)
        remarks = data.get('remarks', '').strip()
        
        # Check if book exists
        book = Library.query.filter_by(book_id=book_id, is_active=True).first()
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        # Return the book
        success, message = book.return_book(student_id)
        
        if not success:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        # Update issue record with damage fee and remarks if provided
        if damage_fee > 0 or remarks:
            issue_record = BookIssue.query.filter_by(
                book_id=book_id,
                student_id=student_id
            ).order_by(BookIssue.return_date.desc()).first()
            
            if issue_record:
                if damage_fee > 0:
                    issue_record.damage_fee = damage_fee
                if remarks:
                    issue_record.remarks = remarks
                db.session.commit()
        
        logger.info(f"Book returned: {book_id} from {student_id}")
        
        return jsonify({
            'success': True,
            'message': message,
            'book': book.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error returning book: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to return book',
            'error': str(e)
        }), 500


@library.route('/student/<student_id>/books', methods=['GET'])
@jwt_required()
def get_student_books(student_id):
    """Get all books issued to a student"""
    try:
        # Get current user info
        current_user_id = get_jwt_identity()
        
        # Students can only view their own books, staff can view any student's books
        # This will be handled by checking user role in a proper implementation
        
        # Check if student exists
        student = Student.query.filter_by(roll_no=student_id).first()
        if not student:
            return jsonify({
                'success': False,
                'message': 'Student not found'
            }), 404
        
        # Get active and historical book issues
        active_issues = BookIssue.get_student_issues(student_id, active_only=True)
        all_issues = BookIssue.get_student_issues(student_id, active_only=False)
        
        # Calculate totals
        total_late_fees = sum(issue.late_fee for issue in all_issues if issue.late_fee > 0)
        total_damage_fees = sum(issue.damage_fee for issue in all_issues if issue.damage_fee > 0)
        
        return jsonify({
            'success': True,
            'student': {
                'roll_no': student.roll_no,
                'name': student.name,
                'email': student.email
            },
            'active_books': [issue.to_dict() for issue in active_issues],
            'book_history': [issue.to_dict() for issue in all_issues[-20:]],  # Last 20 records
            'statistics': {
                'total_books_issued': len(all_issues),
                'currently_issued': len(active_issues),
                'overdue_books': len([issue for issue in active_issues if issue.is_overdue]),
                'total_late_fees': total_late_fees,
                'total_damage_fees': total_damage_fees
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching student books: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch student books',
            'error': str(e)
        }), 500


@library.route('/renew', methods=['POST'])
@jwt_required()
def renew_book():
    """Renew a book (Students and Staff)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['issue_id']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return validation_error
        
        issue_id = data['issue_id']
        additional_days = data.get('additional_days', 14)
        
        # Get the issue record
        issue_record = BookIssue.query.get(issue_id)
        if not issue_record:
            return jsonify({
                'success': False,
                'message': 'Issue record not found'
            }), 404
        
        # Renew the book
        success, message = issue_record.renew_book(additional_days)
        
        if not success:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        logger.info(f"Book renewed: Issue ID {issue_id}")
        
        return jsonify({
            'success': True,
            'message': message,
            'issue': issue_record.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error renewing book: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to renew book',
            'error': str(e)
        }), 500


@library.route('/overdue', methods=['GET'])
@staff_required
def get_overdue_books():
    """Get all overdue books (Staff only)"""
    try:
        overdue_issues = BookIssue.get_overdue_books()
        
        return jsonify({
            'success': True,
            'overdue_books': [issue.to_dict() for issue in overdue_issues],
            'total_overdue': len(overdue_issues)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching overdue books: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch overdue books',
            'error': str(e)
        }), 500


@library.route('/statistics', methods=['GET'])
@staff_required
def get_library_statistics():
    """Get library statistics (Staff only)"""
    try:
        stats = BookIssue.get_library_statistics()
        
        # Add additional statistics
        # Most popular books
        popular_books_query = db.session.query(
            Library.book_id,
            Library.title,
            Library.author,
            db.func.count(BookIssue.id).label('issue_count')
        ).join(BookIssue).group_by(Library.book_id)\
         .order_by(db.func.count(BookIssue.id).desc())\
         .limit(10)
        
        popular_books = []
        for book_id, title, author, count in popular_books_query:
            popular_books.append({
                'book_id': book_id,
                'title': title,
                'author': author,
                'issue_count': count
            })
        
        stats['popular_books'] = popular_books
        
        # Category-wise distribution
        category_stats = db.session.query(
            Library.category,
            db.func.count(Library.book_id).label('book_count')
        ).filter_by(is_active=True)\
         .group_by(Library.category)\
         .order_by(db.func.count(Library.book_id).desc()).all()
        
        stats['category_distribution'] = [
            {'category': cat or 'Uncategorized', 'book_count': count} 
            for cat, count in category_stats
        ]
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching library statistics: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch library statistics',
            'error': str(e)
        }), 500


@library.route('/search', methods=['GET'])
@jwt_required()
def search_books():
    """Advanced book search with multiple filters"""
    try:
        # Get search parameters
        title = request.args.get('title', '').strip()
        author = request.args.get('author', '').strip()
        isbn = request.args.get('isbn', '').strip()
        category = request.args.get('category', '').strip()
        available_only = request.args.get('available_only', 'false').lower() == 'true'
        
        # Build query
        query = Library.query.filter_by(is_active=True)
        
        if title:
            query = query.filter(Library.title.contains(title))
        if author:
            query = query.filter(Library.author.contains(author))
        if isbn:
            query = query.filter(Library.isbn.contains(isbn))
        if category:
            query = query.filter_by(category=category)
        if available_only:
            query = query.filter(Library.available_copies > 0)
        
        books = query.order_by(Library.title).all()
        
        return jsonify({
            'success': True,
            'books': [book.to_dict() for book in books],
            'total_results': len(books)
        }), 200
        
    except Exception as e:
        logger.error(f"Error searching books: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to search books',
            'error': str(e)
        }), 500


@library.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """Get all book categories"""
    try:
        categories = db.session.query(Library.category)\
                              .filter(Library.is_active == True)\
                              .distinct().all()
        
        category_list = [cat[0] for cat in categories if cat[0]]
        category_list.sort()
        
        return jsonify({
            'success': True,
            'categories': category_list
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch categories',
            'error': str(e)
        }), 500