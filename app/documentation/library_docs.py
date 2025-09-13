"""
Library Management API Documentation
Comprehensive documentation for library-related endpoints
"""

from flask_restx import Resource
from app.documentation import (
    library_ns, book_model, book_issue_model, library_member_model,
    success_model, error_model, pagination_model
)

@library_ns.route('/books')
class BooksAPI(Resource):
    @library_ns.doc('list_books',
        description='''
        **Get Books Catalog**
        
        Retrieve paginated list of books in the library.
        
        **Access Control:** All authenticated users
        
        **Query Parameters:**
        - `page`: Page number (default: 1)
        - `per_page`: Items per page (default: 50, max: 100)
        - `search`: Search by title, author, or ISBN
        - `category`: Filter by book category
        - `available_only`: Show only available books
        - `author`: Filter by author
        - `publisher`: Filter by publisher
        - `sort_by`: Sort field (title, author, publication_year)
        
        **Search Features:**
        - Full-text search across title, author, description
        - Advanced filtering options
        - Availability status
        ''',
        security='Bearer Auth')
    @library_ns.marshal_list_with(book_model, code=200, description='Books retrieved successfully')
    @library_ns.response(401, 'Authentication required', error_model)
    def get(self):
        """Get library books catalog"""
        pass

@library_ns.route('/issues')
class BookIssuesAPI(Resource):
    @library_ns.doc('list_issues',
        description='''
        **Get Book Issues**
        
        Retrieve book issue records.
        
        **Access Control:**
        - **Admin/Staff/Library**: Can view all issues
        - **Students**: Can view their own issues only
        
        **Query Parameters:**
        - `student_roll`: Filter by student
        - `book_id`: Filter by book
        - `status`: Filter by issue status (issued, returned, overdue)
        - `from_date`, `to_date`: Date range filter
        ''',
        security='Bearer Auth')
    @library_ns.marshal_list_with(book_issue_model, code=200, description='Issues retrieved')
    @library_ns.response(401, 'Authentication required', error_model)
    def get(self):
        """Get book issue records"""
        pass

    @library_ns.doc('issue_book',
        description='''
        **Issue Book (Library Staff Only)**
        
        Issue a book to a student.
        
        **Access Control:** Library Staff and Admin only
        
        **Process:**
        1. Validates student membership
        2. Checks book availability
        3. Verifies issue limits
        4. Creates issue record
        5. Updates book status
        ''',
        security='Bearer Auth')
    @library_ns.expect(book_issue_model, validate=True)
    @library_ns.marshal_with(book_issue_model, code=201, description='Book issued successfully')
    @library_ns.response(400, 'Validation errors', error_model)
    @library_ns.response(401, 'Authentication required', error_model)
    @library_ns.response(403, 'Library staff access required', error_model)
    @library_ns.response(404, 'Book or student not found', error_model)
    @library_ns.response(409, 'Book not available or limit exceeded', error_model)
    def post(self):
        """Issue book to student"""
        pass
