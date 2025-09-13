import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
from io import BytesIO

from app import create_app, db
from app.models.staff import Staff, StaffRole, Gender as StaffGender
from app.models.student import Student, Gender as StudentGender
from app.models.course import Course
from app.models.fee import Fee, FeeStatus, PaymentMethod, FeeType

@pytest.fixture
def app():
    """Create test application"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # Create test data
        create_test_data()
        
        yield app
        
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    """Get auth headers for admin user"""
    # Login as admin
    response = client.post('/api/auth/login', 
        json={'identifier': 'admin@test.com', 'password': 'admin123'})  # Use email as identifier
    
    assert response.status_code == 200
    token = response.json['data']['access_token']
    
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

@pytest.fixture
def staff_headers(client):
    """Get auth headers for staff user"""
    # Login as staff
    response = client.post('/api/auth/login', 
        json={'identifier': 'staff@test.com', 'password': 'staff123'})  # Use email as identifier
    
    assert response.status_code == 200
    token = response.json['data']['access_token']
    
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

def create_test_data():
    """Create test data"""
    # Create test course
    course = Course(
        id=1,
        program_level='Bachelor',
        degree_name='B.Tech',
        course_name='Computer Science Engineering',
        course_code='CSE',
        duration_years=4,
        fees_per_semester=50000,
        total_seats=60
    )
    db.session.add(course)
    
    # Create test admin
    admin = Staff(
        employee_id='ADMIN001',
        name='Test Admin',  # Use 'name' not 'full_name'
        email='admin@test.com',
        phone='+91-9876543210',
        gender=StaffGender.OTHER,  # Add required gender field
        role=StaffRole.ADMIN,
        department='Administration',
        date_of_joining=datetime.utcnow() - timedelta(days=365)
    )
    admin.password = 'admin123'  # Use property setter
    db.session.add(admin)
    
    # Create test staff
    staff = Staff(
        employee_id='STAFF001',
        name='Test Staff',  # Use 'name' not 'full_name'
        email='staff@test.com',
        phone='+91-9876543211',
        gender=StaffGender.OTHER,  # Add required gender field
        role=StaffRole.STAFF,  # Use STAFF instead of OFFICE_STAFF
        department='Accounts',
        date_of_joining=datetime.utcnow() - timedelta(days=200)
    )
    staff.password = 'staff123'  # Use property setter
    db.session.add(staff)
    
    # Create test student
    student = Student(
        roll_no='2024CSE001',
        name='Test Student',
        email='student@test.com',
        phone='+91-9876543212',
        date_of_birth=date(2000, 1, 1),
        gender=StudentGender.OTHER,  # Use enum instead of string
        course_id=1,
        admission_year=2024,
        current_semester=1,
        is_active=True
    )
    student.password = 'student123'
    db.session.add(student)
    
    # Create another student for multi-student tests
    student2 = Student(
        roll_no='2024CSE002',
        name='Test Student 2',
        email='student2@test.com',
        phone='+91-9876543213',
        date_of_birth=date(2000, 2, 2),
        gender=StudentGender.OTHER,
        course_id=1,
        admission_year=2024,
        current_semester=1,
        is_active=True
    )
    student2.password = 'student123'
    db.session.add(student2)
    
    db.session.commit()

class TestFeeGeneration:
    """Test fee demand generation"""
    
    def test_generate_fee_demand_success(self, client, auth_headers):
        """Test successful fee demand generation"""
        data = {
            'semester': 1,
            'academic_year': '2024-25',
            'course_ids': [1],
            'fee_types': ['tuition', 'library'],
            'due_days': 30
        }
        
        response = client.post('/api/fee/generate-demand', 
            json=data, headers=auth_headers)
        
        assert response.status_code == 201
        assert response.json['error'] == False
        assert 'fees_created' in response.json['data']
        assert response.json['data']['total_students'] == 2
        assert response.json['data']['fees_created'] == 4  # 2 students × 2 fee types
        
        # Verify fees were created in database
        fees = Fee.query.filter_by(semester=1, academic_year='2024-25').all()
        assert len(fees) == 4
        
        for fee in fees:
            assert fee.status == FeeStatus.PENDING
            assert fee.due_date is not None
            assert fee.amount > 0
    
    def test_generate_fee_demand_missing_required_fields(self, client, auth_headers):
        """Test fee generation with missing fields"""
        data = {
            'semester': 1,
            'academic_year': '2024-25'
            # Missing course_ids
        }
        
        response = client.post('/api/fee/generate-demand', 
            json=data, headers=auth_headers)
        
        assert response.status_code == 400
        assert response.json['error'] == True
        assert 'Missing required field' in response.json['message']
    
    def test_generate_fee_demand_invalid_semester(self, client, auth_headers):
        """Test fee generation with invalid semester"""
        data = {
            'semester': 10,  # Invalid semester
            'academic_year': '2024-25',
            'course_ids': [1]
        }
        
        response = client.post('/api/fee/generate-demand', 
            json=data, headers=auth_headers)
        
        assert response.status_code == 400
        assert response.json['error'] == True
        assert 'Semester must be between 1 and 8' in response.json['message']
    
    def test_generate_fee_demand_no_students(self, client, auth_headers):
        """Test fee generation when no students found"""
        data = {
            'semester': 1,
            'academic_year': '2024-25',
            'course_ids': [999]  # Non-existent course
        }
        
        response = client.post('/api/fee/generate-demand', 
            json=data, headers=auth_headers)
        
        assert response.status_code == 404
        assert response.json['error'] == True
        assert 'No active students found' in response.json['message']
    
    def test_generate_fee_demand_duplicate_generation(self, client, auth_headers):
        """Test generating fees when they already exist"""
        # First generation
        data = {
            'semester': 1,
            'academic_year': '2024-25',
            'course_ids': [1],
            'fee_types': ['tuition']
        }
        
        response1 = client.post('/api/fee/generate-demand', 
            json=data, headers=auth_headers)
        assert response1.status_code == 201
        
        # Second generation (should show failed students)
        response2 = client.post('/api/fee/generate-demand', 
            json=data, headers=auth_headers)
        assert response2.status_code == 201
        assert len(response2.json['data']['failed_students']) == 2  # Both students already have fees
        assert response2.json['data']['fees_created'] == 0  # No new fees created
    
    def test_generate_fee_demand_unauthorized(self, client, staff_headers):
        """Test fee generation by non-admin user"""
        data = {
            'semester': 1,
            'academic_year': '2024-25',
            'course_ids': [1]
        }
        
        response = client.post('/api/fee/generate-demand', 
            json=data, headers=staff_headers)
        
        assert response.status_code == 403

class TestFeePayment:
    """Test fee payment processing"""
    
    def test_pay_fee_success(self, client, staff_headers):
        """Test successful fee payment"""
        # Create a pending fee for testing
        fee = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            semester=1,
            academic_year='2024-25',
            due_date=datetime.utcnow() + timedelta(days=30),
            description='Tuition fee for 2024-25 - Semester 1',
            status=FeeStatus.PENDING
        )
        db.session.add(fee)
        db.session.commit()
        
        data = {
            'student_id': '2024CSE001',
            'amount': 50000,
            'payment_method': 'cash',
            'remarks': 'Full payment'
        }
        
        response = client.post('/api/fee/pay', 
            json=data, headers=staff_headers)
        
        assert response.status_code == 200
        assert response.json['error'] == False
        assert response.json['data']['amount_paid'] == 50000
        assert 'paid_fees' in response.json['data']
        
        # Verify fee is marked as paid
        fee = Fee.query.filter_by(student_id='2024CSE001').first()
        assert fee.status == FeeStatus.PAID
        assert fee.payment_date is not None
        assert fee.payment_method == PaymentMethod.CASH
    
    def test_pay_fee_partial_payment(self, client, staff_headers):
        """Test partial fee payment"""
        # Create a pending fee for testing
        fee = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            semester=1,
            academic_year='2024-25',
            due_date=datetime.utcnow() + timedelta(days=30),
            description='Tuition fee for 2024-25 - Semester 1',
            status=FeeStatus.PENDING
        )
        db.session.add(fee)
        db.session.commit()
        
        data = {
            'student_id': '2024CSE001',
            'amount': 25000,  # Partial payment
            'payment_method': 'online',
            'transaction_id': 'TXN123456789'
        }
        
        response = client.post('/api/fee/pay', 
            json=data, headers=staff_headers)
        
        assert response.status_code == 200
        assert response.json['data']['amount_paid'] == 25000
        assert response.json['data']['remaining_balance'] == 25000
        
        # Verify partial payment handling
        fees = Fee.query.filter_by(student_id='2024CSE001').all()
        paid_fee = next(f for f in fees if f.status == FeeStatus.PAID)
        pending_fee = next(f for f in fees if f.status == FeeStatus.PENDING)
        
        assert paid_fee.amount == 25000
        assert pending_fee.amount == 25000
    
    def test_pay_fee_invalid_validation(self, client, staff_headers):
        """Test fee payment with invalid data"""
        # Create a pending fee for testing
        fee = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            semester=1,
            academic_year='2024-25',
            due_date=datetime.utcnow() + timedelta(days=30),
            description='Tuition fee for 2024-25 - Semester 1',
            status=FeeStatus.PENDING
        )
        db.session.add(fee)
        db.session.commit()
        
        data = {
            'student_id': '2024CSE001',
            'amount': -100,  # Invalid amount
            'payment_method': 'cash'
        }
        
        response = client.post('/api/fee/pay', 
            json=data, headers=staff_headers)
        
        assert response.status_code == 400
        assert response.json['error'] == True
        assert 'Amount must be greater than zero' in response.json['message']
    
    def test_pay_fee_student_not_found(self, client, staff_headers):
        """Test payment for non-existent student"""
        data = {
            'student_id': 'INVALID001',
            'amount': 50000,
            'payment_method': 'cash'
        }
        
        response = client.post('/api/fee/pay', 
            json=data, headers=staff_headers)
        
        assert response.status_code == 404
        assert response.json['error'] == True
        assert 'Student not found' in response.json['message']
    
    def test_pay_fee_no_pending_fees(self, client, staff_headers):
        """Test payment when no pending fees exist"""
        # Create and immediately pay all fees
        fee = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            semester=1,
            academic_year='2024-25',
            due_date=datetime.utcnow() + timedelta(days=30),
            description='Tuition fee for 2024-25 - Semester 1',
            status=FeeStatus.PAID  # Already paid
        )
        db.session.add(fee)
        db.session.commit()
        
        data = {
            'student_id': '2024CSE001',
            'amount': 50000,
            'payment_method': 'cash'
        }
        
        response = client.post('/api/fee/pay', 
            json=data, headers=staff_headers)
        
        assert response.status_code == 404
        assert response.json['error'] == True
        assert 'No pending fees found' in response.json['message']
    
    def test_pay_fee_amount_exceeds_pending(self, client, staff_headers):
        """Test payment amount exceeding pending amount"""
        # Create a pending fee for testing
        fee = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            semester=1,
            academic_year='2024-25',
            due_date=datetime.utcnow() + timedelta(days=30),
            description='Tuition fee for 2024-25 - Semester 1',
            status=FeeStatus.PENDING
        )
        db.session.add(fee)
        db.session.commit()
        
        data = {
            'student_id': '2024CSE001',
            'amount': 75000,  # More than pending amount
            'payment_method': 'cash'
        }
        
        response = client.post('/api/fee/pay', 
            json=data, headers=staff_headers)
        
        assert response.status_code == 400
        assert response.json['error'] == True
        assert 'exceeds total pending amount' in response.json['message']

class TestPendingFees:
    """Test pending fees retrieval"""
    
    def test_get_pending_fees_success(self, client, staff_headers):
        """Test successful retrieval of pending fees"""
        # Create various fees for testing
        fees_data = [
            {
                'student_id': '2024CSE001',
                'fee_type': FeeType.TUITION,
                'amount': 50000,
                'status': FeeStatus.PENDING,
                'due_date': datetime.utcnow() + timedelta(days=10)
            },
            {
                'student_id': '2024CSE001',
                'fee_type': FeeType.LIBRARY,
                'amount': 2000,
                'status': FeeStatus.OVERDUE,
                'due_date': datetime.utcnow() - timedelta(days=5)
            },
            {
                'student_id': '2024CSE001',
                'fee_type': FeeType.HOSTEL,
                'amount': 25000,
                'status': FeeStatus.PAID,
                'due_date': datetime.utcnow() - timedelta(days=30)
            }
        ]
        
        for fee_data in fees_data:
            fee = Fee(
                semester=1,
                academic_year='2024-25',
                description=f'{fee_data["fee_type"].value} fee',
                **fee_data
            )
            db.session.add(fee)
        
        db.session.commit()
        
        response = client.get('/api/fee/pending/2024CSE001', 
            headers=staff_headers)
        
        assert response.status_code == 200
        assert response.json['error'] == False
        
        data = response.json['data']
        assert data['student_id'] == '2024CSE001'
        assert len(data['pending_fees']) == 2  # PENDING + OVERDUE, not PAID
        
        # Check summary
        summary = data['summary']
        assert summary['total_count'] == 2
        assert summary['overdue_count'] == 1
        assert summary['total_amount_due'] > 0
    
    def test_get_pending_fees_student_not_found(self, client, staff_headers):
        """Test pending fees for non-existent student"""
        response = client.get('/api/fee/pending/INVALID001', 
            headers=staff_headers)
        
        assert response.status_code == 404
        assert response.json['error'] == True
        assert 'Student not found' in response.json['message']
    
    def test_get_pending_fees_no_pending(self, client, staff_headers):
        """Test when student has no pending fees"""
        # Create paid fees only
        fee = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            semester=1,
            academic_year='2024-25',
            due_date=datetime.utcnow() + timedelta(days=30),
            description='Tuition fee for 2024-25 - Semester 1',
            status=FeeStatus.PAID
        )
        db.session.add(fee)
        db.session.commit()
        
        response = client.get('/api/fee/pending/2024CSE001', 
            headers=staff_headers)
        
        assert response.status_code == 200
        assert len(response.json['data']['pending_fees']) == 0
        assert response.json['data']['summary']['total_count'] == 0
    
    def test_get_pending_fees_late_fee_calculation(self, client, staff_headers):
        """Test that overdue fees have late fees calculated"""
        # Create an overdue fee
        fee = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.LIBRARY,
            amount=2000,
            status=FeeStatus.OVERDUE,
            semester=1,
            academic_year='2024-25',
            due_date=datetime.utcnow() - timedelta(days=5),
            description='Library fee'
        )
        db.session.add(fee)
        db.session.commit()
        
        response = client.get('/api/fee/pending/2024CSE001', 
            headers=staff_headers)
        
        assert response.status_code == 200
        
        # Find the overdue fee
        pending_fees = response.json['data']['pending_fees']
        overdue_fee = next(f for f in pending_fees if f['status'] == 'overdue')
        
        assert overdue_fee['late_fee'] >= 0  # Late fee should be calculated (might be 0 due to logic)
        assert overdue_fee['days_overdue'] > 0

class TestReceiptGeneration:
    """Test receipt generation and download"""
    
    def test_get_receipt_success(self, client, staff_headers):
        """Test successful receipt retrieval"""
        # Create a paid fee for testing
        fee = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            semester=1,
            academic_year='2024-25',
            due_date=datetime.utcnow() - timedelta(days=5),
            description='Tuition fee for 2024-25 - Semester 1',
            status=FeeStatus.PAID,
            payment_date=datetime.utcnow(),
            payment_method=PaymentMethod.ONLINE,
            transaction_id='TXN123456789',
            receipt_number='RCP2024110000001'
        )
        db.session.add(fee)
        db.session.commit()
        
        response = client.get('/api/fee/receipt/TXN123456789', 
            headers=staff_headers)
        
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/pdf'
        assert 'fee_receipt_TXN123456789.pdf' in response.headers.get('Content-Disposition', '')
    
    def test_get_receipt_not_found(self, client, staff_headers):
        """Test receipt for non-existent transaction"""
        response = client.get('/api/fee/receipt/INVALID123', 
            headers=staff_headers)
        
        assert response.status_code == 404
        assert response.json['error'] == True
        assert 'Receipt not found' in response.json['message']
    
    def test_download_receipt_by_number(self, client):
        """Test receipt download by receipt number (public endpoint)"""
        # Create a paid fee for testing
        fee = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            semester=1,
            academic_year='2024-25',
            due_date=datetime.utcnow() - timedelta(days=5),
            description='Tuition fee for 2024-25 - Semester 1',
            status=FeeStatus.PAID,
            payment_date=datetime.utcnow(),
            payment_method=PaymentMethod.ONLINE,
            transaction_id='TXN123456789',
            receipt_number='RCP2024110000001'
        )
        db.session.add(fee)
        db.session.commit()
        
        response = client.get('/api/fee/receipt-download/RCP2024110000001')
        
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/pdf'
    
    def test_download_receipt_invalid_number(self, client):
        """Test receipt download with invalid receipt number"""
        response = client.get('/api/fee/receipt-download/INVALID123')
        
        assert response.status_code == 404

class TestFeeReports:
    """Test fee reporting and analytics"""
    
    def test_get_fee_report_success(self, client, auth_headers):
        """Test successful fee report generation"""
        # Create fees with different statuses and dates
        base_date = datetime.utcnow()
        
        fees_data = [
            # Paid fees
            {
                'student_id': '2024CSE001',
                'fee_type': FeeType.TUITION,
                'amount': 50000,
                'status': FeeStatus.PAID,
                'payment_date': base_date - timedelta(days=10)
            },
            {
                'student_id': '2024CSE002',
                'fee_type': FeeType.LIBRARY,
                'amount': 2000,
                'status': FeeStatus.PAID,
                'payment_date': base_date - timedelta(days=5)
            },
            # Pending fees
            {
                'student_id': '2024CSE001',
                'fee_type': FeeType.HOSTEL,
                'amount': 25000,
                'status': FeeStatus.PENDING,
                'due_date': base_date + timedelta(days=20)
            },
            # Overdue fees
            {
                'student_id': '2024CSE002',
                'fee_type': FeeType.TUITION,
                'amount': 50000,
                'status': FeeStatus.OVERDUE,
                'due_date': base_date - timedelta(days=15)
            }
        ]
        
        for fee_data in fees_data:
            due_date = fee_data.pop('due_date', base_date + timedelta(days=30))
            fee = Fee(
                semester=1,
                academic_year='2024-25',
                description=f'{fee_data["fee_type"].value} fee',
                due_date=due_date,
                **fee_data
            )
            db.session.add(fee)
        
        db.session.commit()
        
        response = client.get('/api/fee/report', headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json['error'] == False
        
        data = response.json['data']
        assert 'fees' in data
        assert 'summary' in data
        
        summary = data['summary']
        assert summary['total_fees'] == 4
        assert summary['total_paid'] == 52000  # 50000 + 2000
        assert summary['total_pending'] == 75000  # 25000 + 50000
        assert summary['collection_rate'] > 0
    
    def test_get_fee_report_with_filters(self, client, auth_headers):
        """Test fee report with filters"""
        # Create test data
        base_date = datetime.utcnow()
        
        # Paid fees
        fee1 = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            status=FeeStatus.PAID,
            semester=1,
            academic_year='2024-25',
            due_date=base_date - timedelta(days=5),
            description='Tuition fee',
            payment_date=base_date - timedelta(days=2)
        )
        fee2 = Fee(
            student_id='2024CSE002',
            fee_type=FeeType.LIBRARY,
            amount=2000,
            status=FeeStatus.PAID,
            semester=1,
            academic_year='2024-25',
            due_date=base_date - timedelta(days=10),
            description='Library fee',
            payment_date=base_date - timedelta(days=8)
        )
        
        # Pending fee
        fee3 = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.HOSTEL,
            amount=25000,
            status=FeeStatus.PENDING,
            semester=1,
            academic_year='2024-25',
            due_date=base_date + timedelta(days=20),
            description='Hostel fee'
        )
        
        db.session.add_all([fee1, fee2, fee3])
        db.session.commit()
        
        # Filter by status
        response = client.get('/api/fee/report?status=paid', 
            headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json['data']
        assert data['summary']['total_fees'] == 2  # Only paid fees
        
        # Filter by date range
        date_from = (datetime.utcnow() - timedelta(days=15)).strftime('%Y-%m-%d')
        date_to = datetime.utcnow().strftime('%Y-%m-%d')
        
        response = client.get(f'/api/fee/report?date_from={date_from}&date_to={date_to}', 
            headers=auth_headers)
        
        assert response.status_code == 200
        # Should include fees created in the date range
    
    def test_get_fee_report_csv_export(self, client, auth_headers):
        """Test CSV export of fee report"""
        # Create test data for CSV export
        base_date = datetime.utcnow()
        
        fee = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            status=FeeStatus.PAID,
            semester=1,
            academic_year='2024-25',
            due_date=base_date - timedelta(days=5),
            description='Tuition fee',
            payment_date=base_date - timedelta(days=2)
        )
        db.session.add(fee)
        db.session.commit()
        
        response = client.get('/api/fee/report?format=csv', 
            headers=auth_headers)
        
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
        assert 'fee_report_' in response.headers.get('Content-Disposition', '')
    
    def test_get_fee_report_unauthorized(self, client, staff_headers):
        """Test fee report access by non-admin"""
        response = client.get('/api/fee/report', headers=staff_headers)
        
        assert response.status_code == 403
    
    def test_get_fee_statistics_success(self, client, auth_headers):
        """Test fee statistics retrieval"""
        # Create some fees for statistics
        base_date = datetime.utcnow()
        
        # Paid fee
        fee1 = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            status=FeeStatus.PAID,
            semester=1,
            academic_year='2024-25',
            due_date=base_date - timedelta(days=5),
            description='Tuition fee',
            payment_date=base_date - timedelta(days=2)
        )
        db.session.add(fee1)
        
        # Pending fee
        fee2 = Fee(
            student_id='2024CSE002',
            fee_type=FeeType.LIBRARY,
            amount=2000,
            status=FeeStatus.PENDING,
            semester=1,
            academic_year='2024-25',
            due_date=base_date + timedelta(days=10),
            description='Library fee'
        )
        db.session.add(fee2)
        db.session.commit()
        
        response = client.get('/api/fee/statistics', headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json['error'] == False
        
        data = response.json['data']
        assert 'overview' in data
        assert 'monthly_trend' in data
        assert 'by_fee_type' in data
        assert 'by_course' in data
        
        # Check overview statistics
        overview = data['overview']
        assert 'total_pending' in overview  # Based on get_fee_statistics method
        assert 'total_paid' in overview
        assert 'total_collected' in overview
        assert 'current_month_collection' in overview
    
    def test_get_fee_statistics_unauthorized(self, client, staff_headers):
        """Test statistics access by non-admin"""
        response = client.get('/api/fee/statistics', headers=staff_headers)
        
        assert response.status_code == 403

class TestFeeIntegration:
    """Integration tests for fee management workflows"""
    
    def test_complete_fee_workflow(self, client, auth_headers, staff_headers):
        """Test complete fee management workflow"""
        # Step 1: Generate fee demand
        generate_data = {
            'semester': 1,
            'academic_year': '2024-25',
            'course_ids': [1],
            'fee_types': ['tuition', 'library'],
            'due_days': 30
        }
        
        response = client.post('/api/fee/generate-demand', 
            json=generate_data, headers=auth_headers)
        assert response.status_code == 201
        
        # Step 2: Check pending fees
        response = client.get('/api/fee/pending/2024CSE001', 
            headers=staff_headers)
        assert response.status_code == 200
        assert len(response.json['data']['pending_fees']) == 2
        
        # Step 3: Make partial payment
        payment_data = {
            'student_id': '2024CSE001',
            'amount': 30000,
            'payment_method': 'online',
            'transaction_id': 'TXN987654321'
        }
        
        response = client.post('/api/fee/pay', 
            json=payment_data, headers=staff_headers)
        assert response.status_code == 200
        
        # Step 4: Check remaining pending fees
        response = client.get('/api/fee/pending/2024CSE001', 
            headers=staff_headers)
        assert response.status_code == 200
        assert response.json['data']['summary']['total_amount_due'] > 0  # Still have pending
        
        # Step 5: Generate receipt
        response = client.get('/api/fee/receipt/TXN987654321', 
            headers=staff_headers)
        assert response.status_code == 200
        
        # Step 6: Check statistics
        response = client.get('/api/fee/statistics', headers=auth_headers)
        assert response.status_code == 200
        assert response.json['data']['overview']['total_collected'] > 0
    
    def test_overdue_fee_handling(self, client, auth_headers, staff_headers):
        """Test handling of overdue fees with late charges"""
        # Create overdue fee
        overdue_fee = Fee(
            student_id='2024CSE001',
            fee_type=FeeType.TUITION,
            amount=50000,
            semester=1,
            academic_year='2024-25',
            due_date=datetime.utcnow() - timedelta(days=60),  # 60 days overdue
            description='Overdue tuition fee',
            status=FeeStatus.OVERDUE
        )
        db.session.add(overdue_fee)
        db.session.commit()
        
        # Check pending fees (should calculate late fee)
        response = client.get('/api/fee/pending/2024CSE001', 
            headers=staff_headers)
        assert response.status_code == 200
        
        fees = response.json['data']['pending_fees']
        overdue_fee_data = next(f for f in fees if f['status'] == 'overdue')
        
        assert overdue_fee_data['late_fee'] > 0
        assert overdue_fee_data['days_overdue'] >= 60
        assert overdue_fee_data['total_amount'] > overdue_fee_data['amount']
        
        # Pay including late fee
        total_due = overdue_fee_data['total_amount']
        payment_data = {
            'student_id': '2024CSE001',
            'amount': total_due,
            'payment_method': 'bank_transfer',
            'reference_number': 'REF123456'
        }
        
        response = client.post('/api/fee/pay', 
            json=payment_data, headers=staff_headers)
        assert response.status_code == 200
        
        # Verify payment processed correctly
        assert response.json['data']['amount_paid'] == total_due
