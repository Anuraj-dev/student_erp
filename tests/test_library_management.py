import pytest
import json
from datetime import datetime, timedelta

from app import create_app, db
from app.models.library import Library, BookIssue
from app.models.student import Student, Gender as StudentGender
from app.models.staff import Staff, StaffRole, Gender as StaffGender
from app.models.course import Course


class TestLibraryManagement:
    """Test cases for Library Management System"""
    
    @pytest.fixture
    def app(self):
        """Create application for testing"""
        app = create_app('testing')
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture
    def auth_headers(self, app, client):
        """Create authentication headers for testing"""
        with app.app_context():
            # Create test staff for authentication
            staff = Staff(
                name="Test Librarian",
                email="librarian@test.edu",
                phone="9876543210",
                role=StaffRole.STAFF,
                gender=StaffGender.MALE
            )
            staff.password = "password123"
            db.session.add(staff)
            db.session.commit()
            
            # Login and get token
            response = client.post('/api/auth/login', json={
                'identifier': 'librarian@test.edu',
                'password': 'password123'
            })
            data = json.loads(response.data)
            token = data['data']['access_token']
            
            return {'Authorization': f'Bearer {token}'}
    
    @pytest.fixture
    def sample_data(self, app):
        """Create sample data for testing"""
        with app.app_context():
            # Create course
            course = Course(
                program_level="UG",
                degree_name="B.Tech",
                course_name="Computer Science",
                course_code="CS"
            )
            db.session.add(course)
            db.session.flush()
            
            # Create student
            student = Student(
                roll_no="2024CS001",
                name="Test Student",
                email="student@test.edu",
                phone="9876543210",
                gender=StudentGender.MALE,
                date_of_birth=datetime(2000, 1, 1).date(),
                course_id=course.id,
                admission_year=2024
            )
            student.password = "password123"
            db.session.add(student)
            
            # Create books
            books = [
                Library(
                    book_id="LB0001",
                    title="Introduction to Algorithms",
                    author="Cormen, Leiserson, Rivest, Stein",
                    isbn="9780262033848",
                    publisher="MIT Press",
                    category="Computer Science",
                    total_copies=3,
                    available_copies=3
                ),
                Library(
                    book_id="LB0002",
                    title="Clean Code",
                    author="Robert C. Martin",
                    isbn="9780132350884",
                    publisher="Prentice Hall",
                    category="Computer Science",
                    total_copies=2,
                    available_copies=2
                )
            ]
            
            for book in books:
                db.session.add(book)
            
            db.session.commit()
            
            return {
                'student_id': student.roll_no,
                'book_ids': [book.book_id for book in books]
            }
    
    def test_get_books(self, client, auth_headers, sample_data):
        """Test getting all books"""
        response = client.get('/api/library/books', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['books']) == 2
        assert 'pagination' in data
    
    def test_search_books(self, client, auth_headers, sample_data):
        """Test book search functionality"""
        # Search by title
        response = client.get(
            '/api/library/books?search=Algorithms',
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['books']) == 1
        assert "Algorithms" in data['books'][0]['title']
    
    def test_get_book_details(self, client, auth_headers, sample_data):
        """Test getting book details"""
        book_id = sample_data['book_ids'][0]
        response = client.get(f'/api/library/books/{book_id}', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['book']['book_id'] == book_id
        assert 'issue_history' in data['book']
    
    def test_add_book(self, client, auth_headers):
        """Test adding a new book"""
        book_data = {
            'title': 'Python Programming',
            'author': 'John Doe',
            'isbn': '1234567890123',
            'publisher': 'Tech Publishers',
            'category': 'Programming',
            'total_copies': 5,
            'shelf_location': 'A1-B2'
        }
        
        response = client.post('/api/library/books', 
                             json=book_data, headers=auth_headers)
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['book']['title'] == book_data['title']
        assert data['book']['available_copies'] == book_data['total_copies']
    
    def test_issue_book(self, client, auth_headers, sample_data):
        """Test issuing a book to student"""
        issue_data = {
            'book_id': sample_data['book_ids'][0],
            'student_id': sample_data['student_id']
        }
        
        response = client.post('/api/library/issue',
                             json=issue_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert "issued successfully" in data['message']
    
    def test_return_book(self, client, auth_headers, sample_data, app):
        """Test returning a book from student"""
        # First issue a book
        with app.app_context():
            book = Library.query.filter_by(book_id=sample_data['book_ids'][0]).first()
            book.issue_book(sample_data['student_id'])
        
        return_data = {
            'book_id': sample_data['book_ids'][0],
            'student_id': sample_data['student_id']
        }
        
        response = client.post('/api/library/return',
                             json=return_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert "returned successfully" in data['message']
    
    def test_get_student_books(self, client, auth_headers, sample_data, app):
        """Test getting books issued to a student"""
        # First issue a book
        with app.app_context():
            book = Library.query.filter_by(book_id=sample_data['book_ids'][0]).first()
            book.issue_book(sample_data['student_id'])
        
        response = client.get(f'/api/library/student/{sample_data["student_id"]}/books',
                            headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['active_books']) == 1
        assert 'statistics' in data
    
    def test_get_library_statistics(self, client, auth_headers, sample_data):
        """Test getting library statistics"""
        response = client.get('/api/library/statistics', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'statistics' in data
        assert 'total_books' in data['statistics']
        assert 'available_books' in data['statistics']
    
    def test_book_renewal(self, client, auth_headers, sample_data, app):
        """Test book renewal functionality"""
        # First issue a book
        with app.app_context():
            book = Library.query.filter_by(book_id=sample_data['book_ids'][0]).first()
            success, message = book.issue_book(sample_data['student_id'])
            assert success
            
            # Get the issue record
            issue = BookIssue.query.filter_by(
                book_id=book.book_id,
                student_id=sample_data['student_id'],
                return_date=None
            ).first()
            
            renewal_data = {
                'issue_id': issue.id,
                'additional_days': 7
            }
            
        response = client.post('/api/library/renew',
                             json=renewal_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert "renewed successfully" in data['message']
    
    def test_get_overdue_books(self, client, auth_headers, sample_data, app):
        """Test getting overdue books"""
        # Create an overdue book issue
        with app.app_context():
            student = Student.query.filter_by(roll_no=sample_data['student_id']).first()
            book = Library.query.filter_by(book_id=sample_data['book_ids'][0]).first()
            
            # Create overdue issue
            overdue_issue = BookIssue(
                book_id=book.book_id,
                student_id=student.roll_no,
                issue_date=datetime.utcnow() - timedelta(days=20),
                due_date=datetime.utcnow() - timedelta(days=5)  # 5 days overdue
            )
            db.session.add(overdue_issue)
            db.session.commit()
        
        response = client.get('/api/library/overdue', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['total_overdue'] > 0
    
    def test_get_categories(self, client, auth_headers, sample_data):
        """Test getting book categories"""
        response = client.get('/api/library/categories', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'Computer Science' in data['categories']
    
    def test_advanced_search(self, client, auth_headers, sample_data):
        """Test advanced book search"""
        response = client.get('/api/library/search?title=Algorithms&category=Computer Science',
                            headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['books']) == 1
        assert data['books'][0]['category'] == 'Computer Science'


if __name__ == '__main__':
    pytest.main([__file__])
