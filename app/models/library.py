from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import json
from app import db


class Library(db.Model):
    """Library model for book management and issue/return tracking"""
    
    __tablename__ = 'library'
    
    # Primary key
    book_id = Column(String(20), primary_key=True)  # Book ID like LB001, LB002, etc.
    
    # Book details
    title = Column(String(200), nullable=False)
    author = Column(String(100), nullable=False)
    isbn = Column(String(20), unique=True)
    publisher = Column(String(100))
    publication_year = Column(Integer)
    category = Column(String(50))  # Subject category
    
    # Inventory details
    total_copies = Column(Integer, nullable=False, default=1)
    available_copies = Column(Integer, nullable=False, default=1)
    
    # Issue tracking
    issued_to = Column(JSON)  # JSON array of student IDs who have issued this book
    
    # Book condition and location
    shelf_location = Column(String(20))
    condition = Column(String(20), default="Good")  # Good, Fair, Poor, Damaged
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps  
    added_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships - Issue/Return records
    issue_records = relationship('BookIssue', back_populates='book', lazy='dynamic')
    
    def __repr__(self):
        return f'<Book {self.book_id}: {self.title} ({self.available_copies}/{self.total_copies} available)>'
    
    @property
    def issued_copies(self):
        """Calculate number of copies currently issued"""
        return self.total_copies - self.available_copies
    
    def to_dict(self):
        """Convert book object to dictionary"""
        return {
            'book_id': self.book_id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'publisher': self.publisher,
            'publication_year': self.publication_year,
            'category': self.category,
            'total_copies': self.total_copies,
            'available_copies': self.available_copies,
            'issued_copies': self.issued_copies,
            'issued_to': self.get_issued_to_list(),
            'shelf_location': self.shelf_location,
            'condition': self.condition,
            'is_active': self.is_active,
            'added_on': self.added_on.isoformat() if self.added_on else None,
            'updated_on': self.updated_on.isoformat() if self.updated_on else None
        }
    
    def get_issued_to_list(self):
        """Get list of students who have issued this book"""
        if self.issued_to:
            if isinstance(self.issued_to, list):
                return self.issued_to
            try:
                return json.loads(self.issued_to) if isinstance(self.issued_to, str) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def set_issued_to_list(self, student_list):
        """Set list of students who have issued this book"""
        self.issued_to = student_list if isinstance(student_list, list) else []
    
    def is_available(self):
        """Check if book is available for issue"""
        return self.available_copies > 0 and self.is_active
    
    def issue_book(self, student_id):
        """Issue book to a student"""
        if not self.is_available():
            return False, "Book not available for issue"
        
        # Check if student already has this book
        issued_list = self.get_issued_to_list()
        if student_id in issued_list:
            return False, "Student already has this book issued"
        
        # Update availability and issued list
        self.available_copies -= 1
        issued_list.append(student_id)
        self.set_issued_to_list(issued_list)
        
        # Create issue record
        issue_record = BookIssue(
            book_id=self.book_id,
            student_id=student_id,
            issue_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=14)  # 14 days loan period
        )
        db.session.add(issue_record)
        db.session.commit()
        
        return True, f"Book issued successfully. Due date: {issue_record.due_date.strftime('%Y-%m-%d')}"
    
    def return_book(self, student_id):
        """Return book from a student"""
        issued_list = self.get_issued_to_list()
        if student_id not in issued_list:
            return False, "Book not issued to this student"
        
        # Find the active issue record
        issue_record = BookIssue.query.filter_by(
            book_id=self.book_id,
            student_id=student_id,
            return_date=None
        ).first()
        
        if not issue_record:
            return False, "No active issue record found"
        
        # Calculate late fee if overdue
        late_fee = 0
        if datetime.utcnow() > issue_record.due_date:
            days_late = (datetime.utcnow() - issue_record.due_date).days
            late_fee = days_late * 5  # ₹5 per day late fee
        
        # Update availability and issued list
        self.available_copies += 1
        issued_list.remove(student_id)
        self.set_issued_to_list(issued_list)
        
        # Update issue record
        issue_record.return_date = datetime.utcnow()
        issue_record.late_fee = late_fee
        
        db.session.commit()
        
        if late_fee > 0:
            return True, f"Book returned successfully. Late fee: ₹{late_fee}"
        return True, "Book returned successfully"
    
    @staticmethod
    def generate_book_id():
        """Generate unique book ID"""
        # Get count of existing books
        existing_count = Library.query.count()
        return f"LB{str(existing_count + 1).zfill(4)}"
    
    @staticmethod
    def search_books(query, category=None):
        """Search books by title, author, or ISBN"""
        search_query = Library.query.filter(Library.is_active == True)
        
        if query:
            search_filter = (
                Library.title.contains(query) |
                Library.author.contains(query) |
                Library.isbn.contains(query)
            )
            search_query = search_query.filter(search_filter)
        
        if category:
            search_query = search_query.filter(Library.category == category)
        
        return search_query.all()
    
    @staticmethod
    def get_available_books():
        """Get all available books"""
        return Library.query.filter(
            Library.is_active == True,
            Library.available_copies > 0
        ).all()
    
    @staticmethod
    def get_popular_books(limit=10):
        """Get most issued books"""
        # This would require more complex query in production
        return Library.query.filter(Library.is_active == True).limit(limit).all()


class BookIssue(db.Model):
    """Book issue/return tracking model"""
    
    __tablename__ = 'book_issues'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    book_id = Column(String(20), ForeignKey('library.book_id'), nullable=False, index=True)
    student_id = Column(String(20), ForeignKey('students.roll_no'), nullable=False, index=True)
    
    # Issue details
    issue_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)
    
    # Fees and penalties
    late_fee = Column(Integer, default=0, nullable=False)  # In rupees
    damage_fee = Column(Integer, default=0, nullable=False)  # In rupees
    
    # Additional details
    remarks = Column(Text)
    renewed_count = Column(Integer, default=0, nullable=False)  # Number of renewals
    
    # Relationships
    book = relationship('Library', back_populates='issue_records')
    student = relationship('Student', back_populates='book_issues')
    
    def __repr__(self):
        return f'<BookIssue {self.id}: {self.book_id} to {self.student_id}>'
    
    @property
    def is_returned(self):
        """Check if book is returned"""
        return self.return_date is not None
    
    @property
    def is_overdue(self):
        """Check if book is overdue"""
        return not self.is_returned and datetime.utcnow() > self.due_date
    
    @property
    def days_overdue(self):
        """Get number of days overdue"""
        if self.is_overdue:
            return (datetime.utcnow() - self.due_date).days
        return 0
    
    def to_dict(self):
        """Convert issue record to dictionary"""
        return {
            'id': self.id,
            'book_id': self.book_id,
            'book_title': self.book.title if self.book else None,
            'student_id': self.student_id,
            'student_name': self.student.name if self.student else None,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'is_returned': self.is_returned,
            'is_overdue': self.is_overdue,
            'days_overdue': self.days_overdue,
            'late_fee': self.late_fee,
            'damage_fee': self.damage_fee,
            'remarks': self.remarks,
            'renewed_count': self.renewed_count
        }
    
    def renew_book(self, additional_days=14):
        """Renew book for additional days"""
        if self.is_returned:
            return False, "Book already returned"
        
        if self.renewed_count >= 2:  # Maximum 2 renewals
            return False, "Maximum renewal limit reached"
        
        if self.is_overdue:
            return False, "Cannot renew overdue book"
        
        self.due_date = self.due_date + timedelta(days=additional_days)
        self.renewed_count += 1
        
        db.session.commit()
        return True, f"Book renewed successfully. New due date: {self.due_date.strftime('%Y-%m-%d')}"
    
    @staticmethod
    def get_student_issues(student_id, active_only=True):
        """Get all book issues for a student"""
        query = BookIssue.query.filter_by(student_id=student_id)
        if active_only:
            query = query.filter(BookIssue.return_date.is_(None))
        return query.all()
    
    @staticmethod
    def get_overdue_books():
        """Get all overdue book issues"""
        current_time = datetime.utcnow()
        return BookIssue.query.filter(
            BookIssue.return_date.is_(None),
            BookIssue.due_date < current_time
        ).all()
    
    @staticmethod
    def get_library_statistics():
        """Get library usage statistics"""
        stats = {}
        
        # Total books and availability
        total_books = Library.query.filter_by(is_active=True).count()
        available_books = Library.query.filter(
            Library.is_active == True,
            Library.available_copies > 0
        ).count()
        
        stats['total_books'] = total_books
        stats['available_books'] = available_books
        stats['issued_books'] = total_books - available_books
        
        # Issue statistics
        total_issues = BookIssue.query.count()
        active_issues = BookIssue.query.filter(BookIssue.return_date.is_(None)).count()
        overdue_issues = len(BookIssue.get_overdue_books())
        
        stats['total_issues'] = total_issues
        stats['active_issues'] = active_issues
        stats['overdue_issues'] = overdue_issues
        
        # Monthly statistics
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_issues = BookIssue.query.filter(BookIssue.issue_date >= current_month_start).count()
        monthly_returns = BookIssue.query.filter(
            BookIssue.return_date >= current_month_start
        ).count()
        
        stats['monthly_issues'] = monthly_issues
        stats['monthly_returns'] = monthly_returns
        
        return stats
