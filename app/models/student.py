from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import enum
from app import db


class Gender(enum.Enum):
    """Enumeration for gender"""
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class Student(db.Model):
    """Student model with roll number as primary key"""
    
    __tablename__ = 'students'
    
    # Primary key - Roll Number
    roll_no = Column(String(20), primary_key=True)
    
    # Personal details
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False, unique=True, index=True)
    phone = Column(String(15), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(db.Enum(Gender), nullable=False)
    
    # Address details
    address = Column(Text)
    city = Column(String(50))
    state = Column(String(50))
    pincode = Column(String(10))
    
    # Guardian details
    father_name = Column(String(100))
    mother_name = Column(String(100))
    guardian_phone = Column(String(15))
    guardian_email = Column(String(120))
    
    # Academic details
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False, index=True)
    admission_year = Column(Integer, nullable=False)
    current_semester = Column(Integer, default=1, nullable=False)
    
    # Hostel details
    hostel_id = Column(Integer, ForeignKey('hostels.id'), nullable=True, index=True)
    room_number = Column(String(20))
    
    # Authentication
    password_hash = Column(String(255), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime)
    
    # Timestamps
    registered_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    course = relationship('Course', back_populates='students')
    hostel = relationship('Hostel', back_populates='students')
    admission_application = relationship('AdmissionApplication', back_populates='student', uselist=False)
    fees = relationship('Fee', back_populates='student', lazy='dynamic')
    examinations = relationship('Examination', back_populates='student', lazy='dynamic')
    book_issues = relationship('BookIssue', back_populates='student', lazy='dynamic')
    
    def __init__(self, **kwargs):
        """Initialize student with auto-generated roll number"""
        # Extract course_id and admission_year for roll number generation
        course_id = kwargs.get('course_id')
        admission_year = kwargs.get('admission_year', datetime.now().year)
        
        if course_id and not kwargs.get('roll_no'):
            kwargs['roll_no'] = self.generate_roll_number(course_id, admission_year)
            
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f'<Student {self.roll_no}: {self.name}>'
    
    @property
    def password(self):
        """Password property getter - raises error"""
        raise AttributeError('Password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches stored hash"""
        return check_password_hash(self.password_hash, password)
    
    def set_password(self, password):
        """Set password hash - explicit method for compatibility"""
        self.password_hash = generate_password_hash(password)
    
    @staticmethod
    def generate_roll_number(course_id, admission_year=None):
        """Generate unique roll number format: YEAR + COURSE_CODE + SERIAL"""
        if admission_year is None:
            admission_year = datetime.now().year
            
        # Get course to fetch course code
        from app.models.course import Course
        course = Course.query.get(course_id)
        if not course:
            raise ValueError(f"Course with ID {course_id} not found")
        
        # Get count of existing students for this course and year
        existing_count = Student.query.filter(
            Student.course_id == course_id,
            Student.admission_year == admission_year
        ).count()
        
        # Generate serial number (4 digits)
        serial = str(existing_count + 1).zfill(4)
        
        # Format: YEAR + COURSE_CODE + SERIAL (e.g., 2025CS0001)
        return f"{admission_year}{course.course_code}{serial}"
    
    def to_dict(self, include_sensitive=False):
        """Convert student object to dictionary"""
        data = {
            'roll_no': self.roll_no,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender.value,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'father_name': self.father_name,
            'mother_name': self.mother_name,
            'guardian_phone': self.guardian_phone,
            'guardian_email': self.guardian_email,
            'course_id': self.course_id,
            'course_name': self.course.course_name if self.course else None,
            'course_code': self.course.course_code if self.course else None,
            'admission_year': self.admission_year,
            'current_semester': self.current_semester,
            'hostel_id': self.hostel_id,
            'hostel_name': self.hostel.name if self.hostel else None,
            'room_number': self.room_number,
            'is_active': self.is_active,
            'registered_on': self.registered_on.isoformat() if self.registered_on else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
        if include_sensitive:
            data['updated_on'] = self.updated_on.isoformat() if self.updated_on else None
            
        return data
    
    def get_age(self):
        """Calculate student's age"""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def get_pending_fees(self):
        """Get total pending fees amount"""
        from app.models.fee import FeeStatus
        pending_fees = self.fees.filter_by(status=FeeStatus.PENDING).all()
        return sum(fee.amount for fee in pending_fees)
    
    def get_total_paid_fees(self):
        """Get total paid fees amount"""
        from app.models.fee import FeeStatus
        paid_fees = self.fees.filter_by(status=FeeStatus.PAID).all()
        return sum(fee.amount for fee in paid_fees)
    
    def allocate_hostel(self, hostel_id, room_number=None):
        """Allocate hostel to student"""
        from app.models.hostel import Hostel
        
        # Check if student already has hostel
        if self.hostel_id:
            return False, "Student already allocated to a hostel"
        
        # Check hostel availability
        hostel = Hostel.query.get(hostel_id)
        if not hostel or not hostel.has_available_beds():
            return False, "Hostel not available or no beds available"
        
        # Allocate hostel
        self.hostel_id = hostel_id
        self.room_number = room_number
        hostel.allocate_bed()
        db.session.commit()
        
        return True, "Hostel allocated successfully"
    
    def vacate_hostel(self, reason="Not specified"):
        """Vacate current hostel"""
        if self.hostel_id:
            hostel = self.hostel
            self.hostel_id = None
            self.room_number = None
            # Note: hostel.vacate_bed() will be called from the route
            # to maintain proper transaction handling
            db.session.commit()
            return True, "Hostel vacated successfully"
        return False, "No hostel allocated"
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def promote_semester(self):
        """Promote student to next semester"""
        max_semesters = self.course.duration_years * 2  # 2 semesters per year
        if self.current_semester < max_semesters:
            self.current_semester += 1
            db.session.commit()
            return True, f"Promoted to semester {self.current_semester}"
        return False, "Student already in final semester"
    
    @staticmethod
    def get_by_roll_no(roll_no):
        """Get student by roll number"""
        return Student.query.filter_by(roll_no=roll_no, is_active=True).first()
    
    @staticmethod
    def get_by_email(email):
        """Get student by email"""
        return Student.query.filter_by(email=email, is_active=True).first()
    
    @staticmethod
    def get_by_course(course_id):
        """Get all students of a specific course"""
        return Student.query.filter_by(course_id=course_id, is_active=True).all()
    
    @staticmethod
    def get_by_admission_year(year):
        """Get all students by admission year"""
        return Student.query.filter_by(admission_year=year, is_active=True).all()
    
    @staticmethod
    def get_hostel_students(hostel_id):
        """Get all students in a specific hostel"""
        return Student.query.filter_by(hostel_id=hostel_id, is_active=True).all()
    
    def get_academic_progress(self):
        """Get academic progress summary"""
        total_semesters = self.course.duration_years * 2
        progress_percentage = (self.current_semester / total_semesters) * 100
        
        return {
            'current_semester': self.current_semester,
            'total_semesters': total_semesters,
            'progress_percentage': round(progress_percentage, 2),
            'years_completed': (self.current_semester - 1) // 2,
            'is_final_year': self.current_semester >= (total_semesters - 1)
        }
