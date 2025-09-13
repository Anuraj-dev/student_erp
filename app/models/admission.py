from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import enum
import json
from app import db


class ApplicationStatus(enum.Enum):
    """Enumeration for application status"""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DECLINED = "declined"
    WAITLISTED = "waitlisted"
    DOCUMENTS_PENDING = "documents_pending"


class GeneratedBy(enum.Enum):
    """Enumeration for who generated the application"""
    STUDENT = "student"
    STAFF = "staff"


class Gender(enum.Enum):
    """Enumeration for gender"""
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class AdmissionApplication(db.Model):
    """AdmissionApplication model for managing student applications"""
    
    __tablename__ = 'admission_applications'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Auto-generated application ID
    application_id = Column(String(20), unique=True, nullable=False, index=True)
    
    # Personal details
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False, index=True)
    phone = Column(String(15), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    
    # Address details
    address = Column(Text)
    city = Column(String(50))
    state = Column(String(50))
    pincode = Column(String(10))
    
    # Guardian details
    father_name = Column(String(100))
    mother_name = Column(String(100))
    guardian_name = Column(String(100))  # Generic guardian name
    guardian_phone = Column(String(15))
    guardian_email = Column(String(120))
    
    # Emergency contact
    emergency_contact = Column(String(15))
    
    # Medical information
    medical_conditions = Column(Text)
    
    # Education details
    previous_education = Column(Text)
    
    # Document storage
    documents = Column(Text)  # JSON string of documents
    
    # Academic details
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False, index=True)
    
    # Previous academic records
    tenth_percentage = Column(Integer)  # Out of 100
    twelfth_percentage = Column(Integer)  # Out of 100
    entrance_exam_score = Column(Integer)  # If applicable
    
    # Authentication (for application tracking)
    password_hash = Column(String(255), nullable=False)
    
    # Application details
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.SUBMITTED, nullable=False, index=True)
    generated_by = Column(Enum(GeneratedBy), default=GeneratedBy.STUDENT, nullable=False)
    staff_id = Column(Integer, ForeignKey('staff.id'), nullable=True, index=True)
    student_id = Column(String(20), ForeignKey('students.roll_no'), nullable=True, index=True)  # Set when approved
    
    # Processing details
    remarks = Column(Text)
    rejection_reason = Column(Text)
    processed_on = Column(DateTime)
    
    # Document verification
    documents_verified = Column(Text)  # JSON string of document statuses
    documents_required = Column(Text)  # JSON string of required documents
    
    # Timestamps
    application_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    course = relationship('Course', back_populates='admission_applications')
    processed_by_staff = relationship('Staff', back_populates='processed_applications')
    student = relationship('Student', back_populates='admission_application')
    
    def __init__(self, **kwargs):
        """Initialize application with auto-generated application ID"""
        if not kwargs.get('application_id'):
            kwargs['application_id'] = self.generate_application_id()
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f'<AdmissionApplication {self.application_id}: {self.name} - {self.status.value}>'
    
    @property 
    def full_name(self):
        """Alias for name field to maintain compatibility"""
        return self.name
    
    @full_name.setter
    def full_name(self, value):
        """Setter for full_name alias"""
        self.name = value
    
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
    
    @staticmethod
    def generate_application_id():
        """Generate unique application ID format: ADMYEAR + 6-digit serial"""
        year = datetime.now().year
        
        # Get count of existing applications for current year
        existing_count = AdmissionApplication.query.filter(
            AdmissionApplication.application_date >= datetime(year, 1, 1),
            AdmissionApplication.application_date < datetime(year + 1, 1, 1)
        ).count()
        
        # Generate 6-digit serial number
        serial = str(existing_count + 1).zfill(6)
        
        return f"ADM{year}{serial}"
    
    def to_dict(self, include_sensitive=False):
        """Convert application object to dictionary"""
        data = {
            'id': self.id,
            'application_id': self.application_id,
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
            'tenth_percentage': self.tenth_percentage,
            'twelfth_percentage': self.twelfth_percentage,
            'entrance_exam_score': self.entrance_exam_score,
            'status': self.status.value,
            'generated_by': self.generated_by.value,
            'staff_id': self.staff_id,
            'remarks': self.remarks,
            'rejection_reason': self.rejection_reason,
            'processed_on': self.processed_on.isoformat() if self.processed_on else None,
            'documents_verified': self.get_documents_verified(),
            'documents_required': self.get_documents_required(),
            'application_date': self.application_date.isoformat() if self.application_date else None
        }
        
        if include_sensitive:
            data['updated_on'] = self.updated_on.isoformat() if self.updated_on else None
            
        return data
    
    def get_documents_verified(self):
        """Get documents verification status as dictionary"""
        if self.documents_verified:
            try:
                return json.loads(self.documents_verified)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_documents_verified(self, documents_dict):
        """Set documents verification status"""
        self.documents_verified = json.dumps(documents_dict)
    
    def get_documents_required(self):
        """Get required documents as list"""
        if self.documents_required:
            try:
                return json.loads(self.documents_required)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def set_documents_required(self, documents_list):
        """Set required documents"""
        self.documents_required = json.dumps(documents_list)
    
    def submit_application(self):
        """Submit application - workflow method"""
        if self.status == ApplicationStatus.PENDING:
            # Set default required documents
            default_documents = [
                "10th Mark Sheet", "12th Mark Sheet", "Transfer Certificate",
                "Aadhar Card", "Passport Photo", "Caste Certificate (if applicable)"
            ]
            self.set_documents_required(default_documents)
            
            # Initialize document verification status
            doc_status = {doc: False for doc in default_documents}
            self.set_documents_verified(doc_status)
            
            db.session.commit()
            return True, "Application submitted successfully"
        return False, "Application already submitted"
    
    def approve_application(self, staff_id, remarks=None):
        """Approve application - workflow method"""
        if self.status != ApplicationStatus.PENDING:
            return False, "Application is not in pending status"
        
        # Check if course has available seats
        if not self.course.has_available_seats():
            return False, "No available seats in the selected course"
        
        self.status = ApplicationStatus.APPROVED
        self.staff_id = staff_id
        self.remarks = remarks
        self.processed_on = datetime.utcnow()
        
        # Create student record
        from app.models.student import Student
        student = Student(
            name=self.name,
            email=self.email,
            phone=self.phone,
            date_of_birth=self.date_of_birth,
            gender=self.gender,
            address=self.address,
            city=self.city,
            state=self.state,
            pincode=self.pincode,
            father_name=self.father_name,
            mother_name=self.mother_name,
            guardian_phone=self.guardian_phone,
            guardian_email=self.guardian_email,
            course_id=self.course_id,
            admission_year=datetime.now().year
        )
        
        # Set temporary password (should be changed on first login)
        temp_password = f"temp{self.application_id[-4:]}"
        student.password = temp_password
        
        db.session.add(student)
        db.session.commit()
        
        return True, f"Application approved. Student roll number: {student.roll_no}, Temporary password: {temp_password}"
    
    def decline_application(self, staff_id, reason):
        """Decline application - workflow method"""
        if self.status != ApplicationStatus.PENDING:
            return False, "Application is not in pending status"
        
        self.status = ApplicationStatus.DECLINED
        self.staff_id = staff_id
        self.rejection_reason = reason
        self.processed_on = datetime.utcnow()
        
        db.session.commit()
        return True, "Application declined successfully"
    
    def request_documents(self, staff_id, documents_list, remarks=None):
        """Request additional documents - workflow method"""
        self.status = ApplicationStatus.DOCUMENTS_PENDING
        self.staff_id = staff_id
        self.remarks = remarks
        self.set_documents_required(documents_list)
        
        # Initialize document verification status
        doc_status = {doc: False for doc in documents_list}
        self.set_documents_verified(doc_status)
        
        db.session.commit()
        return True, "Document verification request sent"
    
    def get_age_at_application(self):
        """Calculate applicant's age at time of application"""
        app_date = self.application_date.date()
        return app_date.year - self.date_of_birth.year - (
            (app_date.month, app_date.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def is_eligible(self):
        """Check if applicant meets basic eligibility criteria"""
        # Basic age check (typically 17-25 for technical education)
        age = self.get_age_at_application()
        if age < 17 or age > 25:
            return False, "Age not within eligible range (17-25 years)"
        
        # Basic academic criteria
        if self.tenth_percentage and self.tenth_percentage < 60:
            return False, "Minimum 60% required in 10th standard"
        
        if self.twelfth_percentage and self.twelfth_percentage < 60:
            return False, "Minimum 60% required in 12th standard"
        
        return True, "Eligible for admission"
    
    @staticmethod
    def get_by_application_id(application_id):
        """Get application by application ID"""
        return AdmissionApplication.query.filter_by(application_id=application_id).first()
    
    @staticmethod
    def get_by_status(status):
        """Get applications by status"""
        return AdmissionApplication.query.filter_by(status=status).all()
    
    @staticmethod
    def get_by_course(course_id):
        """Get applications by course"""
        return AdmissionApplication.query.filter_by(course_id=course_id).all()
    
    @staticmethod
    def get_pending_applications():
        """Get all pending applications"""
        return AdmissionApplication.query.filter_by(status=ApplicationStatus.PENDING).all()
    
    @staticmethod
    def get_statistics():
        """Get admission statistics"""
        stats = {}
        for status in ApplicationStatus:
            stats[status.value] = AdmissionApplication.query.filter_by(status=status).count()
        
        # Calculate conversion rate
        total_apps = sum(stats.values())
        approved_apps = stats.get('approved', 0)
        stats['conversion_rate'] = (approved_apps / total_apps * 100) if total_apps > 0 else 0
        
        return stats
    
    def update_status(self, new_status, remarks=None, processed_by=None):
        """Update application status with logging"""
        self.status = ApplicationStatus(new_status) if isinstance(new_status, str) else new_status
        self.remarks = remarks
        self.processed_on = datetime.utcnow()
        
        if processed_by:
            self.staff_id = processed_by
        
        # Update the updated_on timestamp
        self.updated_on = datetime.utcnow()
    
    @property
    def last_updated(self):
        """Alias for updated_on to maintain compatibility"""
        return self.updated_on

    def add_missing_fields(self, **kwargs):
        """Add missing fields that might not be in the original model"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
