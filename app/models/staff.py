from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum
from app import db


class StaffRole(enum.Enum):
    """Enumeration for staff roles"""
    ADMIN = "admin"
    STAFF = "staff"
    FACULTY = "faculty"


class Gender(enum.Enum):
    """Enumeration for gender"""
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class Staff(db.Model):
    """Staff model for admin, staff, and faculty members"""
    
    __tablename__ = 'staff'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Personal details
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False, unique=True, index=True)
    phone = Column(String(15), nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    
    # Authentication
    password_hash = Column(String(255), nullable=False)
    
    # Role and permissions
    role = Column(Enum(StaffRole), nullable=False, default=StaffRole.STAFF)
    department = Column(String(100))  # For faculty members
    employee_id = Column(String(20), unique=True)  # Auto-generated
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime)
    
    # Additional details
    address = Column(Text)
    date_of_joining = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    registered_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    processed_applications = relationship('AdmissionApplication', back_populates='processed_by_staff', lazy='dynamic')
    
    def __init__(self, **kwargs):
        """Initialize staff member with auto-generated employee ID"""
        super().__init__(**kwargs)
        if not self.employee_id:
            self.employee_id = self.generate_employee_id()
    
    def __repr__(self):
        return f'<Staff {self.employee_id}: {self.name} ({self.role.value})>'
    
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
    
    def generate_employee_id(self):
        """Generate unique employee ID"""
        year = datetime.now().year
        role_prefix = {
            StaffRole.ADMIN: 'ADM',
            StaffRole.STAFF: 'STF', 
            StaffRole.FACULTY: 'FAC'
        }
        
        # Get count of existing staff of same role
        existing_count = Staff.query.filter_by(role=self.role).count()
        serial = str(existing_count + 1).zfill(4)
        
        return f"{year}{role_prefix[self.role]}{serial}"
    
    def to_dict(self, include_sensitive=False):
        """Convert staff object to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'gender': self.gender.value,
            'role': self.role.value,
            'department': self.department,
            'employee_id': self.employee_id,
            'is_active': self.is_active,
            'address': self.address,
            'date_of_joining': self.date_of_joining.isoformat() if self.date_of_joining else None,
            'registered_on': self.registered_on.isoformat() if self.registered_on else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
        if include_sensitive:
            data['updated_on'] = self.updated_on.isoformat() if self.updated_on else None
            
        return data
    
    def has_permission(self, required_role):
        """Check if staff has required permission level"""
        role_hierarchy = {
            StaffRole.FACULTY: 1,
            StaffRole.STAFF: 2,
            StaffRole.ADMIN: 3
        }
        
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def is_admin(self):
        """Check if staff member is admin"""
        return self.role == StaffRole.ADMIN
    
    def is_staff(self):
        """Check if staff member is staff or admin"""
        return self.role in [StaffRole.STAFF, StaffRole.ADMIN]
    
    def is_faculty(self):
        """Check if staff member is faculty"""
        return self.role == StaffRole.FACULTY
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def get_by_email(email):
        """Get staff by email"""
        return Staff.query.filter_by(email=email, is_active=True).first()
    
    @staticmethod
    def get_by_employee_id(employee_id):
        """Get staff by employee ID"""
        return Staff.query.filter_by(employee_id=employee_id, is_active=True).first()
    
    @staticmethod
    def get_active_staff():
        """Get all active staff members"""
        return Staff.query.filter_by(is_active=True).all()
    
    @staticmethod
    def get_by_role(role):
        """Get staff by role"""
        return Staff.query.filter_by(role=role, is_active=True).all()
    
    def get_processed_applications_count(self):
        """Get count of applications processed by this staff member"""
        return self.processed_applications.count()
    
    @staticmethod
    def create_admin(name, email, phone, password, gender=Gender.OTHER):
        """Create admin user - utility method"""
        admin = Staff(
            name=name,
            email=email,
            phone=phone,
            gender=gender,
            role=StaffRole.ADMIN
        )
        admin.password = password
        
        db.session.add(admin)
        db.session.commit()
        
        return admin
