from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum
from app import db


class FeeStatus(enum.Enum):
    """Enumeration for fee payment status"""
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentMethod(enum.Enum):
    """Enumeration for payment methods"""
    CASH = "cash"
    ONLINE = "online"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    DD = "demand_draft"


class FeeType(enum.Enum):
    """Enumeration for fee types"""
    TUITION = "tuition"
    HOSTEL = "hostel"
    LIBRARY = "library"
    LABORATORY = "laboratory"
    EXAM = "exam"
    MISCELLANEOUS = "miscellaneous"


class Fee(db.Model):
    """Fee model for managing student payments"""
    
    __tablename__ = 'fees'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Student reference
    student_id = Column(String(20), ForeignKey('students.roll_no'), nullable=False, index=True)
    
    # Fee details
    fee_type = Column(Enum(FeeType), nullable=False, default=FeeType.TUITION)
    amount = Column(Integer, nullable=False)  # Amount in rupees
    late_fee = Column(Integer, default=0, nullable=False)  # Late fee in rupees
    discount = Column(Integer, default=0, nullable=False)  # Discount in rupees
    
    # Academic details
    semester = Column(Integer, nullable=False)
    academic_year = Column(String(10), nullable=False)  # Format: 2025-26
    
    # Payment details
    payment_date = Column(DateTime, nullable=True)
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    transaction_id = Column(String(100), nullable=True, unique=True, index=True)
    reference_number = Column(String(100), nullable=True)  # Bank reference, cheque number, etc.
    
    # Status and dates
    status = Column(Enum(FeeStatus), default=FeeStatus.PENDING, nullable=False, index=True)
    due_date = Column(DateTime, nullable=False)
    
    # Additional details
    description = Column(Text)
    receipt_number = Column(String(50), nullable=True, unique=True)
    
    # Processing details
    processed_by = Column(Integer, ForeignKey('staff.id'), nullable=True)  # Staff who processed payment
    remarks = Column(Text)
    
    # Timestamps
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    student = relationship('Student', back_populates='fees')
    processed_by_staff = relationship('Staff', foreign_keys=[processed_by])
    
    def __repr__(self):
        return f'<Fee {self.id}: {self.student_id} - ₹{self.total_amount} ({self.status.value})>'
    
    @property
    def total_amount(self):
        """Calculate total amount including late fee minus discount"""
        return self.amount + self.late_fee - self.discount
    
    @property
    def is_overdue(self):
        """Check if fee is overdue"""
        return (self.status == FeeStatus.PENDING or self.status == FeeStatus.OVERDUE) and datetime.utcnow() > self.due_date
    
    @property
    def days_overdue(self):
        """Get number of days overdue"""
        if self.status == FeeStatus.OVERDUE or (self.status == FeeStatus.PENDING and datetime.utcnow() > self.due_date):
            return (datetime.utcnow() - self.due_date).days
        return 0
    
    def to_dict(self, include_sensitive=False):
        """Convert fee object to dictionary"""
        data = {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.name if self.student else None,
            'fee_type': self.fee_type.value,
            'amount': self.amount,
            'late_fee': self.late_fee,
            'discount': self.discount,
            'total_amount': self.total_amount,
            'semester': self.semester,
            'academic_year': self.academic_year,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_method': self.payment_method.value if self.payment_method else None,
            'transaction_id': self.transaction_id,
            'reference_number': self.reference_number,
            'status': self.status.value,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'is_overdue': self.is_overdue,
            'days_overdue': self.days_overdue,
            'description': self.description,
            'receipt_number': self.receipt_number,
            'remarks': self.remarks,
            'created_on': self.created_on.isoformat() if self.created_on else None
        }
        
        if include_sensitive:
            data['processed_by'] = self.processed_by
            data['updated_on'] = self.updated_on.isoformat() if self.updated_on else None
            
        return data
    
    def calculate_late_fee(self):
        """Calculate and update late fee based on overdue days"""
        if not self.is_overdue:
            return 0
        
        days_overdue = self.days_overdue
        
        # Late fee calculation: ₹50 per day for first 30 days, then ₹100 per day
        if days_overdue <= 30:
            late_fee = days_overdue * 50
        else:
            late_fee = (30 * 50) + ((days_overdue - 30) * 100)
        
        # Cap late fee at 25% of original amount
        max_late_fee = self.amount * 0.25
        self.late_fee = min(late_fee, max_late_fee)
        
        return self.late_fee
    
    def process_payment(self, payment_method, transaction_id, reference_number=None, processed_by_staff_id=None):
        """Process fee payment"""
        if self.status != FeeStatus.PENDING:
            return False, "Fee is not in pending status"
        
        self.status = FeeStatus.PAID
        self.payment_date = datetime.utcnow()
        self.payment_method = payment_method
        self.transaction_id = transaction_id
        self.reference_number = reference_number
        self.processed_by = processed_by_staff_id
        self.receipt_number = self.generate_receipt_number()
        
        db.session.commit()
        return True, f"Payment processed successfully. Receipt number: {self.receipt_number}"
    
    def generate_receipt_number(self):
        """Generate unique receipt number"""
        year = datetime.now().year
        month = datetime.now().month
        
        # Count receipts for current month
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1)
        else:
            month_end = datetime(year, month + 1, 1)
        
        receipt_count = Fee.query.filter(
            Fee.payment_date >= month_start,
            Fee.payment_date < month_end,
            Fee.status == FeeStatus.PAID
        ).count()
        
        serial = str(receipt_count + 1).zfill(5)
        return f"RCP{year}{str(month).zfill(2)}{serial}"
    
    def cancel_payment(self, reason, staff_id):
        """Cancel a payment"""
        if self.status != FeeStatus.PAID:
            return False, "Only paid fees can be cancelled"
        
        self.status = FeeStatus.CANCELLED
        self.remarks = f"Cancelled: {reason}"
        self.processed_by = staff_id
        
        db.session.commit()
        return True, "Payment cancelled successfully"
    
    def apply_discount(self, discount_amount, reason, staff_id):
        """Apply discount to fee"""
        if discount_amount > self.amount:
            return False, "Discount cannot be greater than fee amount"
        
        self.discount = discount_amount
        self.remarks = f"Discount applied: {reason}"
        self.processed_by = staff_id
        
        db.session.commit()
        return True, f"Discount of ₹{discount_amount} applied successfully"
    
    @staticmethod
    def generate_fee_demand(course_id, semester, academic_year, fee_type=FeeType.TUITION):
        """Generate fee demand for all students of a course"""
        from app.models.student import Student
        from app.models.course import Course
        
        course = Course.query.get(course_id)
        if not course:
            return False, "Course not found"
        
        students = Student.get_by_course(course_id)
        
        # Calculate due date (30 days from now)
        due_date = datetime.utcnow() + timedelta(days=30)
        
        fees_created = 0
        for student in students:
            # Check if fee already exists for this semester
            existing_fee = Fee.query.filter_by(
                student_id=student.roll_no,
                semester=semester,
                academic_year=academic_year,
                fee_type=fee_type
            ).first()
            
            if existing_fee:
                continue
            
            # Create new fee record
            fee = Fee(
                student_id=student.roll_no,
                fee_type=fee_type,
                amount=course.fees_per_semester,
                semester=semester,
                academic_year=academic_year,
                due_date=due_date,
                description=f"{fee_type.value.title()} fee for Semester {semester}"
            )
            
            db.session.add(fee)
            fees_created += 1
        
        db.session.commit()
        return True, f"Fee demand generated for {fees_created} students"
    
    @staticmethod
    def get_pending_fees_by_student(student_id):
        """Get all pending fees for a student"""
        return Fee.query.filter_by(student_id=student_id, status=FeeStatus.PENDING).all()
    
    @staticmethod
    def get_overdue_fees():
        """Get all overdue fees"""
        current_time = datetime.utcnow()
        return Fee.query.filter(
            Fee.status == FeeStatus.PENDING,
            Fee.due_date < current_time
        ).all()
    
    @staticmethod
    def get_fee_statistics():
        """Get fee collection statistics"""
        stats = {}
        
        # Total fees by status
        for status in FeeStatus:
            stats[f'total_{status.value}'] = Fee.query.filter_by(status=status).count()
        
        # Amount statistics
        paid_fees = Fee.query.filter_by(status=FeeStatus.PAID).all()
        pending_fees = Fee.query.filter_by(status=FeeStatus.PENDING).all()
        
        stats['total_collected'] = sum(fee.total_amount for fee in paid_fees)
        stats['total_pending'] = sum(fee.total_amount for fee in pending_fees)
        
        # Monthly collection (current month)
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_fees = Fee.query.filter(
            Fee.status == FeeStatus.PAID,
            Fee.payment_date >= current_month_start
        ).all()
        stats['current_month_collection'] = sum(fee.total_amount for fee in current_month_fees)
        
        return stats
    
    @staticmethod
    def update_overdue_status():
        """Update status of overdue fees - to be called by scheduled job"""
        current_time = datetime.utcnow()
        overdue_fees = Fee.query.filter(
            Fee.status == FeeStatus.PENDING,
            Fee.due_date < current_time
        ).all()
        
        count = 0
        for fee in overdue_fees:
            fee.status = FeeStatus.OVERDUE
            fee.calculate_late_fee()
            count += 1
        
        db.session.commit()
        return count
