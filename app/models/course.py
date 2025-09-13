from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app import db


class Course(db.Model):
    """Course model for academic programs"""
    
    __tablename__ = 'courses'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Course details
    program_level = Column(String(50), nullable=False)  # Diploma, B.Tech, M.Tech, etc.
    degree_name = Column(String(100), nullable=False)   # Engineering, Computer Applications, etc.
    course_name = Column(String(200), nullable=False)   # Computer Science, Mechanical, etc.
    course_code = Column(String(20), nullable=False, unique=True)  # CS, ME, CE, etc.
    duration_years = Column(Integer, nullable=False, default=4)
    
    # Additional details
    description = Column(Text)
    fees_per_semester = Column(Integer, nullable=False, default=50000)  # In rupees
    total_seats = Column(Integer, nullable=False, default=60)
    is_active = Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    students = relationship('Student', back_populates='course', lazy='dynamic')
    admission_applications = relationship('AdmissionApplication', back_populates='course', lazy='dynamic')
    examinations = relationship('Examination', back_populates='course', lazy='dynamic')
    
    def __repr__(self):
        return f'<Course {self.course_code}: {self.course_name}>'
    
    def to_dict(self):
        """Convert course object to dictionary"""
        return {
            'id': self.id,
            'program_level': self.program_level,
            'degree_name': self.degree_name,
            'course_name': self.course_name,
            'course_code': self.course_code,
            'duration_years': self.duration_years,
            'description': self.description,
            'fees_per_semester': self.fees_per_semester,
            'total_seats': self.total_seats,
            'is_active': self.is_active,
            'created_on': self.created_on.isoformat() if self.created_on else None,
            'updated_on': self.updated_on.isoformat() if self.updated_on else None
        }
    
    @staticmethod
    def get_active_courses():
        """Get all active courses"""
        return Course.query.filter_by(is_active=True).all()
    
    @staticmethod
    def get_by_code(course_code):
        """Get course by course code"""
        return Course.query.filter_by(course_code=course_code, is_active=True).first()
    
    def get_enrollment_count(self):
        """Get current enrollment count for this course"""
        return self.students.count()
    
    def get_available_seats(self):
        """Get available seats for admission"""
        return self.total_seats - self.get_enrollment_count()
    
    def has_available_seats(self):
        """Check if course has available seats"""
        return self.get_available_seats() > 0
    
    def is_accepting_applications(self):
        """Check if course is currently accepting applications"""
        return self.is_active and self.has_available_seats()
    
    @property
    def name(self):
        """Get full course name for display"""
        return f"{self.program_level} in {self.course_name}"
