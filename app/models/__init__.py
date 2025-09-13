# Import all models to make them available when this package is imported
from .student import Student, Gender as StudentGender
from .staff import Staff, StaffRole, Gender as StaffGender  
from .course import Course
from .hostel import Hostel
from .admission import AdmissionApplication, ApplicationStatus, GeneratedBy, Gender as AdmissionGender
from .fee import Fee, FeeStatus, PaymentMethod, FeeType
from .library import Library, BookIssue
from .examination import Examination, ExamType, Grade

__all__ = [
    'Student', 'StudentGender',
    'Staff', 'StaffRole', 'StaffGender',
    'Course',
    'Hostel', 
    'AdmissionApplication', 'ApplicationStatus', 'GeneratedBy', 'AdmissionGender',
    'Fee', 'FeeStatus', 'PaymentMethod', 'FeeType',
    'Library', 'BookIssue',
    'Examination', 'ExamType', 'Grade'
]
