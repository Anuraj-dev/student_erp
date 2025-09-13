"""
Test cases for Hostel Management System
Tests all hostel allocation, vacation, and reporting endpoints
"""

import pytest
import json
from datetime import datetime
from app import create_app, db
from app.models.student import Student, Gender as StudentGender
from app.models.staff import Staff, StaffRole, Gender as StaffGender
from app.models.hostel import Hostel
from app.models.course import Course
from flask_jwt_extended import create_access_token


@pytest.fixture(scope='function')
def app():
    """Create application for testing"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def admin_token(app):
    """Create admin token for authentication"""
    with app.app_context():
        additional_claims = {
            'user_type': 'staff',
            'role': 'ADMIN',
            'name': 'Test Admin',
            'email': 'admin@college.edu'
        }
        return create_access_token(
            identity='admin123',
            additional_claims=additional_claims
        )


@pytest.fixture
def staff_token(app):
    """Create staff token for authentication"""
    with app.app_context():
        additional_claims = {
            'user_type': 'staff',
            'role': 'STAFF',
            'name': 'Test Staff',
            'email': 'staff@college.edu'
        }
        return create_access_token(
            identity='staff456',
            additional_claims=additional_claims
        )


@pytest.fixture
def student_token(app):
    """Create student token for authentication"""
    with app.app_context():
        additional_claims = {
            'user_type': 'student',
            'role': 'student',
            'name': 'Test Male Student',
            'email': 'male@student.edu'
        }
        return create_access_token(
            identity='2024CSE001',
            additional_claims=additional_claims
        )


@pytest.fixture
def setup_data(app):
    """Setup test data"""
    with app.app_context():
        # Create admin staff
        admin = Staff(
            employee_id='admin123',
            name='Test Admin',
            email='admin@college.edu',
            phone='9876543210',
            gender=StaffGender.MALE,
            role=StaffRole.ADMIN
        )
        admin.password = 'admin123'
        db.session.add(admin)
        
        # Create regular staff
        staff = Staff(
            employee_id='staff456',
            name='Test Staff',
            email='staff@college.edu',
            phone='9876543211',
            gender=StaffGender.FEMALE,
            role=StaffRole.STAFF
        )
        staff.password = 'staff456'
        db.session.add(staff)
        
        # Create course
        course = Course(
            program_level='UG',
            degree_name='B.Tech',
            course_name='Computer Science Engineering',
            course_code='CSE',
            duration_years=4
        )
        db.session.add(course)
        
        # Create hostels
        boys_hostel = Hostel(
            name='Boys Hostel A',
            hostel_type='Boys',
            warden_name='John Warden',
            warden_phone='9876543212',
            total_beds=100,
            occupied_beds=0,  # No students initially
            address='College Campus, Block A',
            facilities='WiFi, Mess, Study Room',
            monthly_rent=3000,
            security_deposit=10000,
            is_active=True
        )
        db.session.add(boys_hostel)
        
        girls_hostel = Hostel(
            name='Girls Hostel B',
            hostel_type='Girls',
            warden_name='Jane Warden',
            warden_phone='9876543213',
            total_beds=80,
            occupied_beds=1,  # One student allocated (2024CSE003)
            address='College Campus, Block B',
            facilities='WiFi, Mess, Study Room, Gym',
            monthly_rent=3500,
            security_deposit=12000,
            is_active=True
        )
        db.session.add(girls_hostel)
        
        mixed_hostel = Hostel(
            name='Mixed Hostel C',
            hostel_type='Mixed',
            warden_name='Alex Warden',
            warden_phone='9876543214',
            total_beds=60,
            occupied_beds=60,  # Full occupancy
            address='College Campus, Block C',
            facilities='WiFi, Mess',
            monthly_rent=2800,
            security_deposit=8000,
            is_active=True
        )
        db.session.add(mixed_hostel)
        
        # Inactive hostel
        inactive_hostel = Hostel(
            name='Old Hostel D',
            hostel_type='Boys',
            warden_name='Old Warden',
            warden_phone='9876543215',
            total_beds=50,
            occupied_beds=0,
            address='Old Campus',
            facilities='Basic',
            monthly_rent=2000,
            security_deposit=5000,
            is_active=False
        )
        db.session.add(inactive_hostel)
        
        db.session.commit()
        
        # Create students
        male_student = Student(
            roll_no='2024CSE001',
            name='Test Male Student',
            email='male@student.edu',
            phone='9876543216',
            gender=StudentGender.MALE,
            date_of_birth=datetime(2000, 1, 1),
            course_id=course.id,
            admission_year=2024,
            current_semester=1,
            hostel_id=None  # Not allocated initially
        )
        male_student.password = 'student123'
        db.session.add(male_student)
        
        female_student = Student(
            roll_no='2024CSE002',
            name='Test Female Student',
            email='female@student.edu',
            phone='9876543217',
            gender=StudentGender.FEMALE,
            date_of_birth=datetime(2000, 2, 2),
            course_id=course.id,
            admission_year=2024,
            current_semester=1,
            hostel_id=None  # Not allocated initially
        )
        female_student.password = 'student456'
        db.session.add(female_student)
        
        # Student already allocated to hostel
        allocated_student = Student(
            roll_no='2024CSE003',
            name='Allocated Student',
            email='allocated@student.edu',
            phone='9876543218',
            gender=StudentGender.FEMALE,
            date_of_birth=datetime(2000, 3, 3),
            course_id=course.id,
            admission_year=2024,
            current_semester=1,
            hostel_id=girls_hostel.id  # Already allocated to girls hostel
        )
        allocated_student.password = 'student789'
        db.session.add(allocated_student)
        
        db.session.commit()
        
        return {
            'admin': admin,
            'staff': staff,
            'course': course,
            'boys_hostel': boys_hostel,
            'girls_hostel': girls_hostel,
            'mixed_hostel': mixed_hostel,
            'inactive_hostel': inactive_hostel,
            'male_student': male_student,
            'female_student': female_student,
            'allocated_student': allocated_student,
            # Store IDs to avoid DetachedInstanceError
            'boys_hostel_id': boys_hostel.id,
            'girls_hostel_id': girls_hostel.id,
            'mixed_hostel_id': mixed_hostel.id,
            'inactive_hostel_id': inactive_hostel.id,
            'course_id': course.id
        }


class TestHostelAvailable:
    """Test GET /api/hostel/available endpoint"""
    
    def test_get_available_hostels_success(self, client, admin_token, setup_data):
        """Test successful retrieval of available hostels"""
        response = client.get(
            '/api/hostel/available',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        assert 'hostels' in data['data']
        
        # Should return 3 available hostels (boys: 100 available, girls: 79 available)
        hostels = data['data']['hostels']
        assert len(hostels) == 2
        
        # Check structure
        for hostel in hostels:
            assert 'id' in hostel
            assert 'name' in hostel
            assert 'available_beds' in hostel
            assert hostel['available_beds'] > 0
    
    def test_get_available_hostels_with_gender_filter_male(self, client, admin_token, setup_data):
        """Test retrieval with gender filter for male"""
        response = client.get(
            '/api/hostel/available?gender=male',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        hostels = data['data']['hostels']
        # Should return boys hostel only
        assert len(hostels) == 1
        assert hostels[0]['name'] == 'Boys Hostel A'
    
    def test_get_available_hostels_with_gender_filter_female(self, client, admin_token, setup_data):
        """Test retrieval with gender filter for female"""
        response = client.get(
            '/api/hostel/available?gender=female',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        hostels = data['data']['hostels']
        # Should return girls hostel only
        assert len(hostels) == 1
        assert hostels[0]['name'] == 'Girls Hostel B'
    
    def test_get_available_hostels_no_auth(self, client, setup_data):
        """Test endpoint without authentication"""
        response = client.get('/api/hostel/available')
        
        assert response.status_code == 401


class TestHostelAllocate:
    """Test POST /api/hostel/allocate endpoint"""
    
    def test_allocate_hostel_success_male(self, client, staff_token, setup_data):
        """Test successful hostel allocation for male student"""
        data = {
            'student_id': '2024CSE001',
            'hostel_id': setup_data['boys_hostel_id'],
            'room_number': 'A101'
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'data' in response_data
        assert response_data['data']['student_id'] == '2024CSE001'
        assert response_data['data']['hostel_name'] == 'Boys Hostel A'
        assert response_data['data']['room_number'] == 'A101'
    
    def test_allocate_hostel_success_female(self, client, staff_token, setup_data):
        """Test successful hostel allocation for female student"""
        data = {
            'student_id': '2024CSE002',
            'hostel_id': setup_data['girls_hostel_id']
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert response_data['data']['student_id'] == '2024CSE002'
        assert response_data['data']['hostel_name'] == 'Girls Hostel B'
    
    def test_allocate_hostel_missing_fields(self, client, staff_token, setup_data):
        """Test allocation with missing required fields"""
        data = {'student_id': '2024CSE001'}  # Missing hostel_id
        
        response = client.post(
            '/api/hostel/allocate',
            json=data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'student_id and hostel_id are required' in response_data['message']
    
    def test_allocate_hostel_student_not_found(self, client, staff_token, setup_data):
        """Test allocation for non-existent student"""
        data = {
            'student_id': 'NONEXISTENT',
            'hostel_id': setup_data['boys_hostel_id']
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'Student not found' in response_data['message']
    
    def test_allocate_hostel_already_allocated(self, client, staff_token, setup_data):
        """Test allocation for student already having hostel"""
        data = {
            'student_id': '2024CSE003',  # Already allocated
            'hostel_id': setup_data['girls_hostel_id']
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'already allocated' in response_data['message']
    
    def test_allocate_hostel_not_found(self, client, staff_token, setup_data):
        """Test allocation to non-existent hostel"""
        data = {
            'student_id': '2024CSE001',
            'hostel_id': 9999  # Non-existent
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'Hostel not found' in response_data['message']
    
    def test_allocate_hostel_inactive(self, client, staff_token, setup_data):
        """Test allocation to inactive hostel"""
        data = {
            'student_id': '2024CSE001',
            'hostel_id': setup_data['inactive_hostel_id']
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'not active' in response_data['message']
    
    def test_allocate_hostel_no_available_beds(self, client, staff_token, setup_data):
        """Test allocation when no beds available"""
        data = {
            'student_id': '2024CSE001',
            'hostel_id': setup_data['mixed_hostel_id']  # Full occupancy
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'No available beds' in response_data['message']
    
    def test_allocate_hostel_gender_mismatch_male_to_girls(self, client, staff_token, setup_data):
        """Test allocation of male student to girls hostel"""
        data = {
            'student_id': '2024CSE001',  # Male student
            'hostel_id': setup_data['girls_hostel_id']
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'female students only' in response_data['message']
    
    def test_allocate_hostel_gender_mismatch_female_to_boys(self, client, staff_token, setup_data):
        """Test allocation of female student to boys hostel"""
        data = {
            'student_id': '2024CSE002',  # Female student
            'hostel_id': setup_data['boys_hostel_id']
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'male students only' in response_data['message']
    
    def test_allocate_hostel_no_auth(self, client, setup_data):
        """Test allocation without authentication"""
        data = {
            'student_id': '2024CSE001',
            'hostel_id': setup_data['boys_hostel_id']
        }
        
        response = client.post('/api/hostel/allocate', json=data)
        assert response.status_code == 401
    
    def test_allocate_hostel_student_access_denied(self, client, student_token, setup_data):
        """Test that students cannot allocate hostels"""
        data = {
            'student_id': '2024CSE001',
            'hostel_id': setup_data['boys_hostel_id']
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=data,
            headers={'Authorization': f'Bearer {student_token}'}
        )
        
        assert response.status_code == 403


class TestHostelVacate:
    """Test PUT /api/hostel/vacate/{student_id} endpoint"""
    
    def test_vacate_hostel_success(self, client, staff_token, setup_data):
        """Test successful hostel vacation"""
        data = {'reason': 'Graduation completed'}
        
        response = client.put(
            '/api/hostel/vacate/2024CSE003',  # Allocated student
            json=data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'data' in response_data
        assert response_data['data']['student_id'] == '2024CSE003'
        assert response_data['data']['vacation_reason'] == 'Graduation completed'
    
    def test_vacate_hostel_no_reason(self, client, staff_token, setup_data):
        """Test vacation without reason"""
        response = client.put(
            '/api/hostel/vacate/2024CSE003',
            json={},  # Empty JSON object
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert response_data['data']['vacation_reason'] == 'Not specified'
    
    def test_vacate_hostel_student_not_found(self, client, staff_token, setup_data):
        """Test vacation for non-existent student"""
        response = client.put(
            '/api/hostel/vacate/NONEXISTENT',
            json={},  # Empty JSON object
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'Student not found' in response_data['message']
    
    def test_vacate_hostel_not_allocated(self, client, staff_token, setup_data):
        """Test vacation for student without hostel"""
        response = client.put(
            '/api/hostel/vacate/2024CSE001',  # Not allocated
            json={},  # Empty JSON object
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'not allocated' in response_data['message']
    
    def test_vacate_hostel_no_auth(self, client, setup_data):
        """Test vacation without authentication"""
        response = client.put('/api/hostel/vacate/2024CSE003')
        assert response.status_code == 401


class TestHostelOccupancyReport:
    """Test GET /api/hostel/occupancy-report endpoint"""
    
    def test_occupancy_report_success(self, client, admin_token, setup_data):
        """Test successful occupancy report generation"""
        response = client.get(
            '/api/hostel/occupancy-report',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        
        # Check report structure
        report_data = data['data']
        assert 'overall_statistics' in report_data
        assert 'hostel_details' in report_data
        assert 'students_by_hostel' in report_data
        assert 'gender_statistics' in report_data
        
        # Check overall statistics
        stats = report_data['overall_statistics']
        assert 'total_hostels' in stats
        assert 'total_beds' in stats
        assert 'total_occupied' in stats
        assert 'occupancy_percentage' in stats
        
        # Should have 3 active hostels
        assert stats['total_hostels'] == 3
    
    def test_occupancy_report_staff_access_denied(self, client, staff_token, setup_data):
        """Test that regular staff cannot access occupancy report"""
        response = client.get(
            '/api/hostel/occupancy-report',
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 403
    
    def test_occupancy_report_no_auth(self, client, setup_data):
        """Test report without authentication"""
        response = client.get('/api/hostel/occupancy-report')
        assert response.status_code == 401


class TestStudentHostelDetails:
    """Test GET /api/hostel/student/{student_id} endpoint"""
    
    def test_student_hostel_details_allocated(self, client, admin_token, setup_data):
        """Test getting hostel details for allocated student"""
        response = client.get(
            '/api/hostel/student/2024CSE003',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['hostel_allocated'] is True
        assert 'hostel_details' in data['data']
        
        hostel_details = data['data']['hostel_details']
        assert hostel_details['name'] == 'Girls Hostel B'
    
    def test_student_hostel_details_not_allocated(self, client, admin_token, setup_data):
        """Test getting hostel details for non-allocated student"""
        response = client.get(
            '/api/hostel/student/2024CSE001',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['hostel_allocated'] is False
        assert data['data']['hostel_details'] is None
    
    def test_student_hostel_details_not_found(self, client, admin_token, setup_data):
        """Test getting details for non-existent student"""
        response = client.get(
            '/api/hostel/student/NONEXISTENT',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Student not found' in data['message']


class TestHostelStatistics:
    """Test GET /api/hostel/statistics endpoint"""
    
    def test_hostel_statistics_success(self, client, staff_token, setup_data):
        """Test successful statistics retrieval"""
        response = client.get(
            '/api/hostel/statistics',
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        
        stats = data['data']
        assert 'total_hostels' in stats
        assert 'students_with_hostel' in stats
        assert 'students_without_hostel' in stats
        assert 'hostel_types' in stats
        
        # Check hostel type counts
        hostel_types = stats['hostel_types']
        assert hostel_types['boys_hostels'] == 1
        assert hostel_types['girls_hostels'] == 1
        assert hostel_types['mixed_hostels'] == 1
    
    def test_hostel_statistics_no_auth(self, client, setup_data):
        """Test statistics without authentication"""
        response = client.get('/api/hostel/statistics')
        assert response.status_code == 401


class TestHostelIntegration:
    """Integration tests for complete hostel workflows"""
    
    def test_complete_allocation_vacation_flow(self, client, staff_token, setup_data):
        """Test complete flow: allocate then vacate"""
        # First allocate
        allocation_data = {
            'student_id': '2024CSE001',
            'hostel_id': setup_data['boys_hostel_id'],
            'room_number': 'A101'
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=allocation_data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        assert response.status_code == 200
        
        # Then vacate
        vacation_data = {'reason': 'End of semester'}
        
        response = client.put(
            '/api/hostel/vacate/2024CSE001',
            json=vacation_data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        assert response.status_code == 200
        
        # Check that student no longer has hostel
        response = client.get(
            '/api/hostel/student/2024CSE001',
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['hostel_allocated'] is False
    
    def test_hostel_capacity_management(self, client, staff_token, admin_token, setup_data):
        """Test that hostel capacity is properly managed"""
        # Get initial available beds
        response = client.get(
            '/api/hostel/available',
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        initial_data = json.loads(response.data)
        boys_hostel_initial = None
        for hostel in initial_data['data']['hostels']:
            if hostel['name'] == 'Boys Hostel A':
                boys_hostel_initial = hostel['available_beds']
                break
        
        # Allocate student
        allocation_data = {
            'student_id': '2024CSE001',
            'hostel_id': setup_data['boys_hostel_id']
        }
        
        response = client.post(
            '/api/hostel/allocate',
            json=allocation_data,
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        assert response.status_code == 200
        
        # Check available beds decreased
        response = client.get(
            '/api/hostel/available',
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        after_allocation_data = json.loads(response.data)
        boys_hostel_after = None
        for hostel in after_allocation_data['data']['hostels']:
            if hostel['name'] == 'Boys Hostel A':
                boys_hostel_after = hostel['available_beds']
                break
        
        assert boys_hostel_after == boys_hostel_initial - 1
        
        # Vacate student
        response = client.put(
            '/api/hostel/vacate/2024CSE001',
            json={'reason': 'Testing capacity management'},  # Add JSON data
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        assert response.status_code == 200
        
        # Check available beds increased back
        response = client.get(
            '/api/hostel/available',
            headers={'Authorization': f'Bearer {staff_token}'}
        )
        after_vacation_data = json.loads(response.data)
        boys_hostel_final = None
        for hostel in after_vacation_data['data']['hostels']:
            if hostel['name'] == 'Boys Hostel A':
                boys_hostel_final = hostel['available_beds']
                break
        
        assert boys_hostel_final == boys_hostel_initial
