"""
Fee Management API Documentation
Comprehensive documentation for fee-related endpoints
"""

from flask_restx import Resource
from app.documentation import (
    fee_ns, fee_model, fee_payment_model, fee_structure_model,
    success_model, error_model, pagination_model
)

@fee_ns.route('')
class FeesListAPI(Resource):
    @fee_ns.doc('list_fees',
        description='''
        **Get Fee Records**
        
        Retrieve paginated list of fee records with filtering options.
        
        **Access Control:**
        - **Admin/Staff**: Can view all fee records
        - **Students**: Can only view their own fee records
        
        **Query Parameters:**
        - `page`: Page number (default: 1)
        - `per_page`: Items per page (default: 50, max: 100)
        - `student_roll`: Filter by student roll number
        - `fee_type`: Filter by fee type (tuition, hostel, library, etc.)
        - `status`: Filter by payment status (paid, pending, overdue)
        - `semester`: Filter by semester
        - `academic_year`: Filter by academic year
        - `from_date`, `to_date`: Date range filter
        - `amount_min`, `amount_max`: Amount range filter
        
        **Statistics Included:**
        - Total fees collected
        - Pending amount
        - Overdue count
        - Payment method distribution
        ''',
        security='Bearer Auth')
    @fee_ns.marshal_list_with(fee_model, code=200, description='Fee records retrieved successfully')
    @fee_ns.response(401, 'Authentication required', error_model)
    @fee_ns.response(403, 'Insufficient permissions', error_model)
    def get(self):
        """Get paginated list of fee records"""
        pass

    @fee_ns.doc('create_fee_record',
        description='''
        **Create Fee Record (Admin Only)**
        
        Create a new fee record for a student.
        
        **Access Control:** Admin only
        
        **Process:**
        1. Validates student existence
        2. Checks for duplicate fee records
        3. Calculates due date based on fee type
        4. Creates fee record with proper status
        5. Sends notification to student
        
        **Fee Types:**
        - **tuition**: Semester tuition fees
        - **hostel**: Hostel accommodation fees
        - **library**: Library fees and deposits
        - **examination**: Exam registration fees
        - **laboratory**: Lab fees
        - **sports**: Sports and activities fees
        - **transport**: Transportation fees
        - **miscellaneous**: Other institutional fees
        
        **Automatic Calculations:**
        - Late fees after due date
        - Discount applications
        - Tax calculations (if applicable)
        ''',
        security='Bearer Auth')
    @fee_ns.expect(fee_model, validate=True)
    @fee_ns.marshal_with(fee_model, code=201, description='Fee record created successfully')
    @fee_ns.response(400, 'Validation errors', error_model)
    @fee_ns.response(401, 'Authentication required', error_model)
    @fee_ns.response(403, 'Admin access required', error_model)
    @fee_ns.response(409, 'Duplicate fee record', error_model)
    def post(self):
        """Create new fee record (Admin only)"""
        pass

@fee_ns.route('/<int:fee_id>')
class FeeDetailAPI(Resource):
    @fee_ns.doc('get_fee_detail',
        description='''
        **Get Fee Record Details**
        
        Retrieve detailed information about a specific fee record.
        
        **Access Control:**
        - **Admin/Staff**: Can view any fee record
        - **Students**: Can only view their own fee records
        
        **Includes:**
        - Complete fee information
        - Payment history
        - Late fees and penalties
        - Discount applications
        - Receipt download links
        - Payment due calculations
        
        **Path Parameters:**
        - `fee_id`: Unique fee record ID
        ''',
        security='Bearer Auth')
    @fee_ns.marshal_with(fee_model, code=200, description='Fee details retrieved')
    @fee_ns.response(401, 'Authentication required', error_model)
    @fee_ns.response(403, 'Access denied', error_model)
    @fee_ns.response(404, 'Fee record not found', error_model)
    def get(self, fee_id):
        """Get fee record details by ID"""
        pass

    @fee_ns.doc('update_fee_record',
        description='''
        **Update Fee Record (Admin Only)**
        
        Update fee record information.
        
        **Access Control:** Admin only
        
        **Updatable Fields:**
        - Amount (with approval workflow for significant changes)
        - Due date (with notification to student)
        - Fee type and description
        - Discount percentage
        - Status (with proper validation)
        
        **Restrictions:**
        - Cannot modify paid fees (except for corrections)
        - Status changes must follow proper workflow
        - Amount changes require audit trail
        
        **Workflow:**
        1. Validates changes against business rules
        2. Creates audit log entry
        3. Recalculates dependent amounts
        4. Sends notifications if required
        ''',
        security='Bearer Auth')
    @fee_ns.expect(fee_model, validate=True)
    @fee_ns.marshal_with(fee_model, code=200, description='Fee record updated successfully')
    @fee_ns.response(400, 'Validation errors', error_model)
    @fee_ns.response(401, 'Authentication required', error_model)
    @fee_ns.response(403, 'Admin access required', error_model)
    @fee_ns.response(404, 'Fee record not found', error_model)
    @fee_ns.response(409, 'Cannot update paid fee', error_model)
    def put(self, fee_id):
        """Update fee record information"""
        pass

@fee_ns.route('/<int:fee_id>/payment')
class FeePaymentAPI(Resource):
    @fee_ns.doc('process_payment',
        description='''
        **Process Fee Payment**
        
        Process payment for a fee record.
        
        **Access Control:**
        - **Admin/Staff**: Can process payments for any student
        - **Students**: Can pay their own fees only
        
        **Payment Methods:**
        - **online**: Online payment gateway
        - **bank_transfer**: Bank transfer/NEFT
        - **cash**: Cash payment (staff only)
        - **cheque**: Cheque payment
        - **demand_draft**: Demand Draft
        - **upi**: UPI payments
        - **card**: Credit/Debit card
        
        **Process:**
        1. Validates payment amount and method
        2. Processes payment through appropriate gateway
        3. Generates receipt with unique number
        4. Updates fee status
        5. Sends confirmation email/SMS
        6. Records transaction for accounting
        
        **Payment Validation:**
        - Amount must match fee due
        - Payment method must be valid
        - Student account must be active
        - No duplicate payments allowed
        ''',
        security='Bearer Auth')
    @fee_ns.expect(fee_payment_model, validate=True)
    @fee_ns.marshal_with(success_model, code=200, description='Payment processed successfully')
    @fee_ns.response(400, 'Invalid payment details', error_model)
    @fee_ns.response(401, 'Authentication required', error_model)
    @fee_ns.response(403, 'Access denied', error_model)
    @fee_ns.response(404, 'Fee record not found', error_model)
    @fee_ns.response(409, 'Payment already processed', error_model)
    @fee_ns.response(502, 'Payment gateway error', error_model)
    def post(self, fee_id):
        """Process fee payment"""
        pass

@fee_ns.route('/<int:fee_id>/receipt')
class FeeReceiptAPI(Resource):
    @fee_ns.doc('get_receipt',
        description='''
        **Get Fee Receipt**
        
        Retrieve or generate fee payment receipt.
        
        **Access Control:**
        - **Admin/Staff**: Can generate receipts for any payment
        - **Students**: Can get receipts for their own payments only
        
        **Receipt Features:**
        - Official institution letterhead
        - Unique receipt number
        - Complete payment details
        - Student and fee information
        - Authorized signatures
        - QR code for verification
        
        **Formats:**
        - **PDF**: Default downloadable format
        - **JSON**: Digital receipt data
        - **Print**: Print-optimized format
        
        **Query Parameters:**
        - `format`: Response format (pdf, json, print)
        - `download`: Force download (default: true)
        ''',
        security='Bearer Auth')
    @fee_ns.response(200, 'Receipt generated successfully')
    @fee_ns.response(401, 'Authentication required', error_model)
    @fee_ns.response(403, 'Access denied', error_model)
    @fee_ns.response(404, 'Payment not found', error_model)
    @fee_ns.response(422, 'Payment not completed', error_model)
    def get(self, fee_id):
        """Get or generate fee payment receipt"""
        pass

@fee_ns.route('/student/<string:roll_no>')
class StudentFeesAPI(Resource):
    @fee_ns.doc('get_student_fees',
        description='''
        **Get Student Fee Summary**
        
        Retrieve comprehensive fee summary for a specific student.
        
        **Access Control:**
        - **Admin/Staff**: Can view any student's fees
        - **Students**: Can view their own fees only
        
        **Summary Includes:**
        - All pending fees with due dates
        - Payment history with receipts
        - Total paid and outstanding amounts
        - Late fees and penalties
        - Upcoming fee deadlines
        - Payment plan options (if available)
        
        **Query Parameters:**
        - `academic_year`: Filter by academic year
        - `status`: Filter by payment status
        - `include_history`: Include complete payment history
        
        **Dashboard Data:**
        - Quick payment buttons
        - Due date alerts
        - Payment method preferences
        - Installment options
        ''',
        security='Bearer Auth')
    @fee_ns.response(200, 'Student fees retrieved')
    @fee_ns.response(401, 'Authentication required', error_model)
    @fee_ns.response(403, 'Access denied', error_model)
    @fee_ns.response(404, 'Student not found', error_model)
    def get(self, roll_no):
        """Get comprehensive fee summary for student"""
        pass

@fee_ns.route('/overdue')
class OverdueFeesAPI(Resource):
    @fee_ns.doc('get_overdue_fees',
        description='''
        **Get Overdue Fees (Staff Only)**
        
        Retrieve list of all overdue fee payments.
        
        **Access Control:** Staff and Admin only
        
        **Features:**
        - Automatic late fee calculations
        - Days overdue tracking
        - Bulk reminder capabilities
        - Export options for follow-up
        
        **Query Parameters:**
        - `days_overdue`: Filter by days overdue (e.g., >30)
        - `course_id`: Filter by course
        - `amount_min`: Minimum overdue amount
        - `sort_by`: Sort by amount, days, student name
        
        **Actions Available:**
        - Send reminder notifications
        - Generate follow-up reports
        - Apply additional penalties
        - Block student services (if configured)
        ''',
        security='Bearer Auth')
    @fee_ns.response(200, 'Overdue fees retrieved')
    @fee_ns.response(401, 'Authentication required', error_model)
    @fee_ns.response(403, 'Staff access required', error_model)
    def get(self):
        """Get all overdue fee payments"""
        pass

@fee_ns.route('/structure')
class FeeStructureAPI(Resource):
    @fee_ns.doc('get_fee_structure',
        description='''
        **Get Fee Structure**
        
        Retrieve current fee structure for courses.
        
        **Access Control:** All authenticated users
        
        **Structure Includes:**
        - Course-wise fee breakdown
        - Semester-wise amounts
        - Optional fees (hostel, transport, etc.)
        - Discount categories and criteria
        - Late fee policies
        - Payment deadlines
        
        **Query Parameters:**
        - `course_id`: Get structure for specific course
        - `academic_year`: Get structure for specific year
        - `fee_type`: Filter by fee type
        
        **Use Cases:**
        - Student fee planning
        - Admission counseling
        - Financial aid calculations
        ''',
        security='Bearer Auth')
    @fee_ns.marshal_with(fee_structure_model, code=200, description='Fee structure retrieved')
    @fee_ns.response(401, 'Authentication required', error_model)
    def get(self):
        """Get current fee structure"""
        pass

    @fee_ns.doc('update_fee_structure',
        description='''
        **Update Fee Structure (Admin Only)**
        
        Update fee structure for courses.
        
        **Access Control:** Admin only
        
        **Process:**
        1. Validates new structure against existing fees
        2. Applies changes with effective date
        3. Sends notifications to affected students
        4. Creates audit trail
        5. Updates future fee records
        
        **Considerations:**
        - Cannot affect already paid fees
        - Requires approval workflow for major changes
        - Must maintain historical structure data
        - Automatic pro-rating calculations
        ''',
        security='Bearer Auth')
    @fee_ns.expect(fee_structure_model, validate=True)
    @fee_ns.marshal_with(fee_structure_model, code=200, description='Fee structure updated')
    @fee_ns.response(400, 'Validation errors', error_model)
    @fee_ns.response(401, 'Authentication required', error_model)
    @fee_ns.response(403, 'Admin access required', error_model)
    def put(self):
        """Update fee structure (Admin only)"""
        pass

@fee_ns.route('/reports')
class FeeReportsAPI(Resource):
    @fee_ns.doc('generate_fee_reports',
        description='''
        **Generate Fee Reports (Staff Only)**
        
        Generate various fee-related reports.
        
        **Access Control:** Staff and Admin only
        
        **Available Reports:**
        - **collection**: Fee collection summary
        - **outstanding**: Outstanding fees report
        - **defaulters**: Students with overdue payments
        - **refunds**: Fee refund summary
        - **analysis**: Fee trends and analysis
        - **audit**: Payment audit trail
        
        **Query Parameters:**
        - `report_type`: Type of report (required)
        - `from_date`, `to_date`: Date range
        - `course_id`: Filter by course
        - `format`: Output format (pdf, excel, csv)
        - `email`: Email report to specified address
        
        **Features:**
        - Scheduled report generation
        - Email delivery options
        - Custom date ranges
        - Multiple export formats
        ''',
        security='Bearer Auth')
    @fee_ns.response(200, 'Report generated successfully')
    @fee_ns.response(400, 'Invalid report parameters', error_model)
    @fee_ns.response(401, 'Authentication required', error_model)
    @fee_ns.response(403, 'Staff access required', error_model)
    def get(self):
        """Generate fee management reports"""
        pass

@fee_ns.route('/bulk-payment')
class BulkPaymentAPI(Resource):
    @fee_ns.doc('process_bulk_payment',
        description='''
        **Process Bulk Payments (Staff Only)**
        
        Process multiple fee payments in a single operation.
        
        **Access Control:** Staff and Admin only
        
        **Use Cases:**
        - Bank reconciliation
        - Scholarship applications
        - Batch payment processing
        - Fee waiver implementations
        
        **Process:**
        1. Validates all payment records
        2. Processes payments in batches
        3. Generates individual receipts
        4. Creates summary report
        5. Handles failures gracefully
        
        **Input Format:**
        - CSV/Excel file with payment details
        - JSON array of payment records
        - Bank statement reconciliation data
        
        **Validation:**
        - All records validated before processing
        - Duplicate detection
        - Amount verification
        - Student account validation
        ''',
        security='Bearer Auth')
    @fee_ns.response(200, 'Bulk payments processed')
    @fee_ns.response(400, 'Validation errors in bulk data', error_model)
    @fee_ns.response(401, 'Authentication required', error_model)
    @fee_ns.response(403, 'Staff access required', error_model)
    def post(self):
        """Process multiple payments in bulk"""
        pass
