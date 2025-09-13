from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timedelta
from app import db
import enum


class ExamType(enum.Enum):
    """Enumeration for examination types"""
    INTERNAL = "internal"
    SEMESTER = "semester"
    FINAL = "final"
    SUPPLEMENTARY = "supplementary"


class Grade(enum.Enum):
    """Enumeration for grades"""
    O = "O"  # Outstanding (90-100)
    A_PLUS = "A+"  # Excellent (80-89)
    A = "A"  # Very Good (70-79)
    B_PLUS = "B+"  # Good (60-69)
    B = "B"  # Above Average (55-59)
    C = "C"  # Average (50-54)
    P = "P"  # Pass (40-49)
    F = "F"  # Fail (Below 40)
    AB = "AB"  # Absent
    MP = "MP"  # Malpractice


class Examination(db.Model):
    """Examination model for storing exam records and results"""
    
    __tablename__ = 'examinations'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Student and course reference
    student_id = Column(String(20), ForeignKey('students.roll_no'), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False, index=True)
    
    # Exam details
    exam_type = Column(db.Enum(ExamType), nullable=False, default=ExamType.SEMESTER)
    subject_name = Column(String(100), nullable=False)
    subject_code = Column(String(20), nullable=False)
    semester = Column(Integer, nullable=False)
    academic_year = Column(String(10), nullable=False)  # Format: 2025-26
    
    # Exam dates
    exam_date = Column(DateTime, nullable=False)
    result_declared_date = Column(DateTime, nullable=True)
    
    # Marks and grading
    max_marks = Column(Integer, nullable=False, default=100)
    marks_obtained = Column(Integer, nullable=True)  # Null until result is declared
    grade = Column(db.Enum(Grade), nullable=True)
    grade_points = Column(Float, nullable=True)  # For GPA calculation
    
    # Internal assessment breakdown
    internal_marks = Column(Integer, default=0, nullable=False)  # Internal assessment (30 marks)
    external_marks = Column(Integer, default=0, nullable=False)  # External exam (70 marks)
    
    # Status and result
    is_pass = Column(Boolean, nullable=True)  # True if passed, False if failed, None if not declared
    is_absent = Column(Boolean, default=False, nullable=False)
    has_malpractice = Column(Boolean, default=False, nullable=False)
    
    # Additional details
    remarks = Column(Text)
    
    # Processing details
    result_processed_by = Column(Integer, ForeignKey('staff.id'), nullable=True)
    
    # Timestamps
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    student = relationship('Student', back_populates='examinations')
    course = relationship('Course', back_populates='examinations')
    processed_by_staff = relationship('Staff', foreign_keys=[result_processed_by])
    
    def __repr__(self):
        return f'<Examination {self.id}: {self.student_id} - {self.subject_name} ({self.grade or "Pending"})>'
    
    def to_dict(self, include_sensitive=False):
        """Convert examination object to dictionary"""
        data = {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.name if self.student else None,
            'course_id': self.course_id,
            'course_name': self.course.course_name if self.course else None,
            'exam_type': self.exam_type.value,
            'subject_name': self.subject_name,
            'subject_code': self.subject_code,
            'semester': self.semester,
            'academic_year': self.academic_year,
            'exam_date': self.exam_date.isoformat() if self.exam_date else None,
            'result_declared_date': self.result_declared_date.isoformat() if self.result_declared_date else None,
            'max_marks': self.max_marks,
            'marks_obtained': self.marks_obtained,
            'internal_marks': self.internal_marks,
            'external_marks': self.external_marks,
            'grade': self.grade.value if self.grade else None,
            'grade_points': self.grade_points,
            'is_pass': self.is_pass,
            'is_absent': self.is_absent,
            'has_malpractice': self.has_malpractice,
            'remarks': self.remarks,
            'created_on': self.created_on.isoformat() if self.created_on else None
        }
        
        if include_sensitive:
            data['result_processed_by'] = self.result_processed_by
            data['updated_on'] = self.updated_on.isoformat() if self.updated_on else None
            
        return data
    
    def calculate_grade(self):
        """Calculate grade based on marks obtained"""
        if self.is_absent:
            return Grade.AB
        
        if self.has_malpractice:
            return Grade.MP
        
        if self.marks_obtained is None:
            return None
        
        percentage = (self.marks_obtained / self.max_marks) * 100
        
        if percentage >= 90:
            return Grade.O
        elif percentage >= 80:
            return Grade.A_PLUS
        elif percentage >= 70:
            return Grade.A
        elif percentage >= 60:
            return Grade.B_PLUS
        elif percentage >= 55:
            return Grade.B
        elif percentage >= 50:
            return Grade.C
        elif percentage >= 40:
            return Grade.P
        else:
            return Grade.F
    
    def calculate_grade_points(self):
        """Calculate grade points for GPA"""
        grade_point_map = {
            Grade.O: 10.0,
            Grade.A_PLUS: 9.0,
            Grade.A: 8.0,
            Grade.B_PLUS: 7.0,
            Grade.B: 6.0,
            Grade.C: 5.0,
            Grade.P: 4.0,
            Grade.F: 0.0,
            Grade.AB: 0.0,
            Grade.MP: 0.0
        }
        
        return grade_point_map.get(self.grade, 0.0)
    
    def declare_result(self, marks_obtained, internal_marks=None, external_marks=None, 
                      is_absent=False, has_malpractice=False, remarks=None, staff_id=None):
        """Declare examination result"""
        
        self.marks_obtained = marks_obtained if not is_absent and not has_malpractice else 0
        self.internal_marks = internal_marks or 0
        self.external_marks = external_marks or (marks_obtained - (internal_marks or 0))
        self.is_absent = is_absent
        self.has_malpractice = has_malpractice
        self.remarks = remarks
        self.result_processed_by = staff_id
        self.result_declared_date = datetime.utcnow()
        
        # Calculate grade and grade points
        self.grade = self.calculate_grade()
        self.grade_points = self.calculate_grade_points()
        
        # Determine pass/fail status
        if is_absent or has_malpractice:
            self.is_pass = False
        else:
            self.is_pass = marks_obtained >= (self.max_marks * 0.4)  # 40% passing marks
        
        db.session.commit()
        return True, f"Result declared successfully. Grade: {self.grade.value if self.grade else 'N/A'}"
    
    def update_result(self, marks_obtained, remarks=None, staff_id=None):
        """Update examination result"""
        if self.result_declared_date is None:
            return False, "Result not yet declared"
        
        self.marks_obtained = marks_obtained
        self.remarks = remarks
        self.result_processed_by = staff_id
        self.updated_on = datetime.utcnow()
        
        # Recalculate grade and pass status
        self.grade = self.calculate_grade()
        self.grade_points = self.calculate_grade_points()
        self.is_pass = marks_obtained >= (self.max_marks * 0.4)
        
        db.session.commit()
        return True, "Result updated successfully"
    
    @staticmethod
    def get_student_results(student_id, semester=None):
        """Get all results for a student"""
        query = Examination.query.filter_by(student_id=student_id)
        if semester:
            query = query.filter_by(semester=semester)
        return query.order_by(Examination.semester, Examination.subject_name).all()
    
    @staticmethod
    def get_semester_results(course_id, semester, academic_year):
        """Get all results for a semester"""
        return Examination.query.filter_by(
            course_id=course_id,
            semester=semester,
            academic_year=academic_year
        ).all()
    
    @staticmethod
    def calculate_sgpa(student_id, semester):
        """Calculate SGPA (Semester Grade Point Average) for a student"""
        results = Examination.query.filter_by(
            student_id=student_id,
            semester=semester
        ).all()
        
        if not results:
            return 0.0
        
        # Filter out results that don't contribute to GPA (AB, MP)
        valid_results = [r for r in results if r.grade not in [Grade.AB, Grade.MP] and r.grade is not None]
        
        if not valid_results:
            return 0.0
        
        total_grade_points = sum(r.grade_points or 0 for r in valid_results)
        total_subjects = len(valid_results)
        
        return round(total_grade_points / total_subjects, 2)
    
    @staticmethod
    def calculate_cgpa(student_id):
        """Calculate CGPA (Cumulative Grade Point Average) for a student"""
        results = Examination.query.filter_by(student_id=student_id).all()
        
        if not results:
            return 0.0
        
        # Filter out results that don't contribute to GPA
        valid_results = [r for r in results if r.grade not in [Grade.AB, Grade.MP] and r.grade is not None]
        
        if not valid_results:
            return 0.0
        
        total_grade_points = sum(r.grade_points or 0 for r in valid_results)
        total_subjects = len(valid_results)
        
        return round(total_grade_points / total_subjects, 2)
    
    @staticmethod
    def get_class_performance(course_id, semester, academic_year, subject_code=None):
        """Get class performance statistics"""
        query = Examination.query.filter_by(
            course_id=course_id,
            semester=semester,
            academic_year=academic_year
        )
        
        if subject_code:
            query = query.filter_by(subject_code=subject_code)
        
        results = query.all()
        
        if not results:
            return {}
        
        # Filter out absent and malpractice cases for statistics
        valid_results = [r for r in results if not r.is_absent and not r.has_malpractice and r.marks_obtained is not None]
        
        if not valid_results:
            return {'total_students': len(results), 'valid_results': 0}
        
        marks = [r.marks_obtained for r in valid_results]
        
        stats = {
            'total_students': len(results),
            'appeared_students': len(valid_results),
            'absent_students': len([r for r in results if r.is_absent]),
            'malpractice_cases': len([r for r in results if r.has_malpractice]),
            'passed_students': len([r for r in valid_results if r.is_pass]),
            'failed_students': len([r for r in valid_results if not r.is_pass]),
            'pass_percentage': round((len([r for r in valid_results if r.is_pass]) / len(valid_results)) * 100, 2),
            'highest_marks': max(marks),
            'lowest_marks': min(marks),
            'average_marks': round(sum(marks) / len(marks), 2),
            'class_average_percentage': round((sum(marks) / len(marks) / results[0].max_marks) * 100, 2)
        }
        
        return stats
    
    @staticmethod
    def get_pending_results():
        """Get all examinations with pending results"""
        return Examination.query.filter(Examination.result_declared_date.is_(None)).all()
    
    def get_percentage(self):
        """Get percentage for this examination"""
        if self.marks_obtained is None or self.max_marks == 0:
            return 0.0
        return round((self.marks_obtained / self.max_marks) * 100, 2)
