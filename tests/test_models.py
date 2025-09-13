
"""
Database Models Test Script
Tests all database models and their relationships
"""

import os
import sys
from datetime import datetime, date

# Add project root to path
sys.path.append('/home/anuraj-dev/Anuraj-dev/Coding test/ERP_Colllege/student_erp')

from app import create_app, db
from app.models import *

def test_models():
    """Test all database models"""
    app = create_app('testing')
    
    with app.app_context():
        print("🔍 Testing Database Models...")
        print("="*50)
        
        try:
            # Drop and create all tables
            db.drop_all()
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Test Course model
            print("\n📚 Testing Course Model...")
            course = Course(
                program_level="B.Tech",
                degree_name="Engineering", 
                course_name="Computer Science",
                course_code="CS",
                duration_years=4,
                fees_per_semester=75000,
                total_seats=60
            )
            db.session.add(course)
            db.session.commit()
            print(f"✅ Course created: {course}")
            
            # Test Hostel model
            print("\n🏠 Testing Hostel Model...")
            hostel = Hostel(
                name="Boys Hostel A",
                hostel_type="Boys",
                total_beds=100,
                warden_name="Mr. Sharma",
                warden_phone="+91-9876543210",
                monthly_rent=5000
            )
            db.session.add(hostel)
            db.session.commit()
            print(f"✅ Hostel created: {hostel}")
            
            # Test Staff model
            print("\n👨‍💼 Testing Staff Model...")
            staff = Staff(
                name="Dr. Admin User",
                email="admin@college.edu.in",
                phone="+91-9876543211",
                gender=StaffGender.MALE,
                role=StaffRole.ADMIN,
                department="Administration"
            )
            staff.password = "admin123"
            db.session.add(staff)
            db.session.commit()
            print(f"✅ Staff created: {staff}")
            
            # Test AdmissionApplication model
            print("\n📝 Testing AdmissionApplication Model...")
            application = AdmissionApplication(
                name="John Doe",
                email="john.doe@gmail.com",
                phone="+91-9876543212",
                date_of_birth=date(2005, 5, 15),
                gender=AdmissionGender.MALE,
                course_id=course.id,
                father_name="Robert Doe",
                mother_name="Jane Doe",
                tenth_percentage=85,
                twelfth_percentage=78
            )
            application.password = "temp123"
            db.session.add(application)
            db.session.commit()
            print(f"✅ Application created: {application}")
            
            # Test Student model (created after application approval)
            print("\n🎓 Testing Student Model...")
            student = Student(
                name="John Doe",
                email="john.student@college.edu.in",
                phone="+91-9876543212", 
                date_of_birth=date(2005, 5, 15),
                gender=StudentGender.MALE,
                course_id=course.id,
                admission_year=2025,
                father_name="Robert Doe",
                mother_name="Jane Doe"
            )
            student.password = "student123"
            db.session.add(student)
            db.session.commit()
            print(f"✅ Student created: {student}")
            
            # Test Fee model
            print("\n💰 Testing Fee Model...")
            fee = Fee(
                student_id=student.roll_no,
                fee_type=FeeType.TUITION,
                amount=75000,
                semester=1,
                academic_year="2025-26",
                due_date=datetime(2025, 10, 15)
            )
            db.session.add(fee)
            db.session.commit()
            print(f"✅ Fee record created: {fee}")
            
            # Test Library model
            print("\n📖 Testing Library Model...")
            book = Library(
                book_id="LB0001",
                title="Introduction to Computer Science",
                author="John Smith",
                isbn="978-0123456789",
                category="Computer Science",
                total_copies=5,
                available_copies=5
            )
            db.session.add(book)
            db.session.commit()
            print(f"✅ Library book created: {book}")
            
            # Test Examination model
            print("\n📊 Testing Examination Model...")
            exam = Examination(
                student_id=student.roll_no,
                course_id=course.id,
                exam_type=ExamType.SEMESTER,
                subject_name="Programming Fundamentals",
                subject_code="CS101",
                semester=1,
                academic_year="2025-26",
                exam_date=datetime(2025, 12, 1),
                max_marks=100
            )
            db.session.add(exam)
            db.session.commit()
            print(f"✅ Examination record created: {exam}")
            
            # Test relationships
            print("\n🔗 Testing Model Relationships...")
            
            # Student-Course relationship
            print(f"Student {student.roll_no} is enrolled in {student.course.course_name}")
            
            # Course-Student relationship
            enrolled_students = course.students.count()
            print(f"Course {course.course_code} has {enrolled_students} enrolled students")
            
            # Student-Fee relationship
            student_fees = student.fees.count()
            print(f"Student {student.roll_no} has {student_fees} fee records")
            
            # Test model methods
            print("\n🧪 Testing Model Methods...")
            
            # Test roll number generation
            print(f"Generated roll number: {student.roll_no}")
            
            # Test application ID generation
            print(f"Generated application ID: {application.application_id}")
            
            # Test course availability
            print(f"Course available seats: {course.get_available_seats()}")
            
            # Test hostel availability
            print(f"Hostel available beds: {hostel.available_beds}")
            
            # Test fee calculations
            print(f"Fee total amount: ₹{fee.total_amount}")
            
            print("\n✅ ALL MODEL TESTS PASSED!")
            print("="*50)
            print("🎉 Database models are working correctly!")
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        return True

if __name__ == "__main__":
    success = test_models()
    if success:
        print("\n🚀 Ready to proceed with Task 3: Authentication System!")
    else:
        print("\n⚠️ Please fix the model issues before proceeding.")
