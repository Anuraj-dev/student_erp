"""
Admission Management API Documentation
Comprehensive documentation for admission-related endpoints
"""

from flask_restx import Resource
from app.documentation import (
    admission_ns, admission_model, admission_update_model,
    success_model, error_model, pagination_model
)

@admission_ns.route('')
class AdmissionsListAPI(Resource):
    @admission_ns.doc('list_admissions',
        description='''
        **Get Admission Applications**
        
        Retrieve paginated list of admission applications with filtering options.
        
        **Access Control:**
        - **Admin/Staff**: Can view all applications
        - **Applicants**: Can only view their own applications
        
        **Query Parameters:**
        - `page`: Page number (default: 1)
        - `per_page`: Items per page (default: 50, max: 100)
        - `status`: Filter by application status
        - `course_id`: Filter by applied course
        - `application_year`: Filter by application year
        - `from_date`, `to_date`: Date range filter
        - `search`: Search by name, email, or application number
        - `sort_by`: Sort field (name, application_date, status)
        - `sort_order`: Sort direction (asc, desc)
        
        **Application Statuses:**
        - **submitted**: Application submitted, pending review
        - **under_review**: Application being reviewed
        - **interview_scheduled**: Interview scheduled
        - **approved**: Application approved for admission
        - **rejected**: Application rejected
        - **waitlisted**: Application on waiting list
        - **enrolled**: Student has enrolled
        - **cancelled**: Application cancelled by applicant
        
        **Search Features:**
        - Full-text search across applicant details
        - Filter combinations for advanced queries
        - Export capabilities for reports
        ''',
        security='Bearer Auth')
    @admission_ns.marshal_list_with(admission_model, code=200, description='Admissions retrieved successfully')
    @admission_ns.response(401, 'Authentication required', error_model)
    @admission_ns.response(403, 'Insufficient permissions', error_model)
    def get(self):
        """Get paginated list of admission applications"""
        pass

    @admission_ns.doc('create_admission',
        description='''
        **Submit Admission Application**
        
        Submit a new admission application.
        
        **Access Control:** Public (with rate limiting) or authenticated users
        
        **Application Process:**
        1. Validates all required documents
        2. Checks eligibility criteria
        3. Generates unique application number
        4. Creates application record
        5. Sends confirmation email with application number
        6. Initiates document verification process
        
        **Required Documents:**
        - Academic transcripts/mark sheets
        - Entrance exam scores (if applicable)
        - Identity proof (Aadhar/Passport)
        - Category certificate (if applicable)
        - Passport-size photographs
        - Medical certificate (for hostel)
        
        **Validation Rules:**
        - Email uniqueness per application cycle
        - Age and academic eligibility
        - Course capacity limits
        - Application deadline compliance
        
        **Automatic Processing:**
        - Document checklist generation
        - Fee calculation based on category
        - Interview scheduling (if required)
        - Merit list compilation
        ''',
        security='Bearer Auth (Optional)')
    @admission_ns.expect(admission_model, validate=True)
    @admission_ns.marshal_with(admission_model, code=201, description='Admission application submitted')
    @admission_ns.response(400, 'Validation errors or eligibility issues', error_model)
    @admission_ns.response(409, 'Duplicate application or deadline passed', error_model)
    @admission_ns.response(422, 'Missing required documents', error_model)
    @admission_ns.response(429, 'Too many applications from same IP', error_model)
    def post(self):
        """Submit new admission application"""
        pass

@admission_ns.route('/<string:application_no>')
class AdmissionDetailAPI(Resource):
    @admission_ns.doc('get_admission_detail',
        description='''
        **Get Admission Application Details**
        
        Retrieve detailed information about a specific admission application.
        
        **Access Control:**
        - **Admin/Staff**: Can view any application
        - **Applicants**: Can view their own application only
        
        **Includes:**
        - Complete application information
        - Document verification status
        - Interview details (if scheduled)
        - Application status history
        - Fee payment information
        - Admission decision and comments
        - Enrollment details (if admitted)
        
        **Path Parameters:**
        - `application_no`: Unique application number (e.g., APP2024001)
        
        **Status Tracking:**
        - Real-time application status
        - Next steps and requirements
        - Important deadlines
        - Contact information for queries
        ''',
        security='Bearer Auth')
    @admission_ns.marshal_with(admission_model, code=200, description='Admission details retrieved')
    @admission_ns.response(401, 'Authentication required', error_model)
    @admission_ns.response(403, 'Access denied', error_model)
    @admission_ns.response(404, 'Application not found', error_model)
    def get(self, application_no):
        """Get admission application details"""
        pass

    @admission_ns.doc('update_admission',
        description='''
        **Update Admission Application**
        
        Update admission application information.
        
        **Access Control:**
        - **Admin/Staff**: Can update any application and change status
        - **Applicants**: Can update their own application (if editable)
        
        **Editable Fields (by role):**
        
        **Admin/Staff:**
        - Application status and comments
        - Interview scheduling
        - Document verification status
        - Admission decision
        - Course allocation
        
        **Applicants (limited conditions):**
        - Personal information (before review starts)
        - Contact details
        - Document uploads (before deadline)
        - Course preferences (if allowed)
        
        **Business Rules:**
        - Applications under review cannot be edited by applicants
        - Status changes must follow proper workflow
        - Document changes require re-verification
        - Approved applications need admin approval for changes
        
        **Workflow States:**
        1. **Editable**: Applicant can modify all details
        2. **Locked**: Only staff can make changes
        3. **Final**: No modifications allowed without special approval
        ''',
        security='Bearer Auth')
    @admission_ns.expect(admission_update_model, validate=True)
    @admission_ns.marshal_with(admission_model, code=200, description='Application updated successfully')
    @admission_ns.response(400, 'Validation errors', error_model)
    @admission_ns.response(401, 'Authentication required', error_model)
    @admission_ns.response(403, 'Insufficient permissions or application locked', error_model)
    @admission_ns.response(404, 'Application not found', error_model)
    @admission_ns.response(409, 'Application in non-editable state', error_model)
    def put(self, application_no):
        """Update admission application"""
        pass

@admission_ns.route('/<string:application_no>/documents')
class AdmissionDocumentsAPI(Resource):
    @admission_ns.doc('get_application_documents',
        description='''
        **Get Application Documents**
        
        Retrieve list of documents associated with an admission application.
        
        **Access Control:**
        - **Admin/Staff**: Can view documents for any application
        - **Applicants**: Can view their own documents only
        
        **Document Information:**
        - Document type and description
        - Upload timestamp and file details
        - Verification status by staff
        - Download links for verified documents
        - Required vs optional document status
        
        **Document Types:**
        - Academic certificates and transcripts
        - Entrance exam score cards
        - Identity and address proofs
        - Category certificates
        - Photographs and signatures
        - Medical certificates
        - Character certificates
        
        **Verification Status:**
        - **pending**: Uploaded, awaiting verification
        - **verified**: Document verified and approved
        - **rejected**: Document rejected, re-upload required
        - **missing**: Required document not uploaded
        ''',
        security='Bearer Auth')
    @admission_ns.response(200, 'Documents retrieved successfully')
    @admission_ns.response(401, 'Authentication required', error_model)
    @admission_ns.response(403, 'Access denied', error_model)
    @admission_ns.response(404, 'Application not found', error_model)
    def get(self, application_no):
        """Get application documents list"""
        pass

    @admission_ns.doc('upload_document',
        description='''
        **Upload Application Document**
        
        Upload or replace a document for an admission application.
        
        **Access Control:**
        - **Admin/Staff**: Can upload documents for any application
        - **Applicants**: Can upload documents for their own application
        
        **Upload Specifications:**
        - **Allowed formats**: PDF, JPG, JPEG, PNG
        - **Maximum file size**: 5MB per document
        - **Naming convention**: Descriptive filenames required
        - **Quality requirements**: Clear, readable documents only
        
        **Process:**
        1. Validates file format and size
        2. Scans for malware/viruses
        3. Stores with unique identifier
        4. Creates document record
        5. Notifies staff for verification
        6. Updates application checklist
        
        **Business Rules:**
        - Can replace documents until verification
        - Verified documents need approval to replace
        - Some documents are mandatory for processing
        - Document expiry dates are checked
        
        **Multipart Form Data:**
        - `document_type`: Type of document being uploaded
        - `file`: Document file (required)
        - `description`: Optional description
        - `replace_existing`: Replace existing document (boolean)
        ''',
        security='Bearer Auth')
    @admission_ns.response(201, 'Document uploaded successfully')
    @admission_ns.response(400, 'Invalid file format or size', error_model)
    @admission_ns.response(401, 'Authentication required', error_model)
    @admission_ns.response(403, 'Upload not allowed', error_model)
    @admission_ns.response(404, 'Application not found', error_model)
    @admission_ns.response(413, 'File too large', error_model)
    def post(self, application_no):
        """Upload document for application"""
        pass

@admission_ns.route('/<string:application_no>/interview')
class AdmissionInterviewAPI(Resource):
    @admission_ns.doc('get_interview_details',
        description='''
        **Get Interview Details**
        
        Retrieve interview information for an admission application.
        
        **Access Control:**
        - **Admin/Staff**: Can view interview details for any application
        - **Applicants**: Can view their own interview details only
        
        **Interview Information:**
        - Scheduled date, time, and venue
        - Interview panel details
        - Instructions and requirements
        - Online meeting links (if virtual)
        - Status and results
        
        **Interview Types:**
        - **in_person**: Face-to-face interview
        - **virtual**: Online video interview
        - **telephonic**: Phone interview
        - **group**: Group discussion/interview
        
        **Status Updates:**
        - **scheduled**: Interview scheduled
        - **completed**: Interview completed
        - **rescheduled**: Interview rescheduled
        - **cancelled**: Interview cancelled
        - **no_show**: Applicant didn't attend
        ''',
        security='Bearer Auth')
    @admission_ns.response(200, 'Interview details retrieved')
    @admission_ns.response(401, 'Authentication required', error_model)
    @admission_ns.response(403, 'Access denied', error_model)
    @admission_ns.response(404, 'Application or interview not found', error_model)
    def get(self, application_no):
        """Get interview details for application"""
        pass

    @admission_ns.doc('schedule_interview',
        description='''
        **Schedule Interview (Staff Only)**
        
        Schedule or reschedule interview for an admission application.
        
        **Access Control:** Staff and Admin only
        
        **Scheduling Process:**
        1. Checks applicant availability preferences
        2. Verifies panel member availability
        3. Books venue or creates online meeting
        4. Sends interview invitation email
        5. Creates calendar appointments
        6. Updates application status
        
        **Required Information:**
        - Interview date and time
        - Interview type and venue
        - Panel member assignments
        - Special instructions (if any)
        
        **Automatic Actions:**
        - Email notifications to applicant
        - Calendar invites to panel members
        - SMS reminders (if configured)
        - Document preparation checklist
        
        **Business Rules:**
        - Must be during business hours
        - Panel members must be available
        - Minimum notice period required
        - Venue capacity considerations
        ''',
        security='Bearer Auth')
    @admission_ns.response(201, 'Interview scheduled successfully')
    @admission_ns.response(400, 'Invalid scheduling parameters', error_model)
    @admission_ns.response(401, 'Authentication required', error_model)
    @admission_ns.response(403, 'Staff access required', error_model)
    @admission_ns.response(404, 'Application not found', error_model)
    @admission_ns.response(409, 'Scheduling conflict', error_model)
    def post(self, application_no):
        """Schedule interview for application"""
        pass

@admission_ns.route('/<string:application_no>/status')
class AdmissionStatusAPI(Resource):
    @admission_ns.doc('update_application_status',
        description='''
        **Update Application Status (Staff Only)**
        
        Update the status of an admission application.
        
        **Access Control:** Staff and Admin only
        
        **Status Workflow:**
        1. **submitted** → **under_review**
        2. **under_review** → **interview_scheduled** (if required)
        3. **interview_scheduled** → **approved/rejected/waitlisted**
        4. **approved** → **enrolled** (when student completes enrollment)
        5. **waitlisted** → **approved** (if seats become available)
        
        **Status Change Actions:**
        
        **Approved:**
        - Sends admission offer letter
        - Calculates fee structure
        - Creates enrollment checklist
        - Reserves course seat
        
        **Rejected:**
        - Sends rejection letter with feedback
        - Releases application slot
        - Updates statistics
        
        **Waitlisted:**
        - Sends waitlist notification
        - Sets up automatic promotion check
        - Maintains position tracking
        
        **Required Fields:**
        - New status (required)
        - Comments/reason for change
        - Effective date (defaults to current)
        - Notify applicant (boolean, default: true)
        ''',
        security='Bearer Auth')
    @admission_ns.response(200, 'Status updated successfully')
    @admission_ns.response(400, 'Invalid status transition', error_model)
    @admission_ns.response(401, 'Authentication required', error_model)
    @admission_ns.response(403, 'Staff access required', error_model)
    @admission_ns.response(404, 'Application not found', error_model)
    def put(self, application_no):
        """Update application status with workflow validation"""
        pass

@admission_ns.route('/statistics')
class AdmissionStatisticsAPI(Resource):
    @admission_ns.doc('get_admission_statistics',
        description='''
        **Get Admission Statistics (Staff Only)**
        
        Retrieve comprehensive statistics about admission applications.
        
        **Access Control:** Staff and Admin only
        
        **Statistics Include:**
        - Total applications by status
        - Course-wise application distribution
        - Admission funnel analysis
        - Geographic distribution of applicants
        - Gender and category-wise statistics
        - Interview completion rates
        - Conversion rates (application to enrollment)
        - Time-based trends and comparisons
        
        **Query Parameters:**
        - `year`: Filter by admission year
        - `course_id`: Filter by specific course
        - `from_date`, `to_date`: Date range for applications
        - `breakdown_by`: Group statistics by (course, month, category)
        
        **Dashboard Metrics:**
        - Applications today/this week
        - Pending reviews count
        - Interview scheduling backlog
        - Seat availability by course
        - Revenue projections
        ''',
        security='Bearer Auth')
    @admission_ns.response(200, 'Statistics retrieved successfully')
    @admission_ns.response(401, 'Authentication required', error_model)
    @admission_ns.response(403, 'Staff access required', error_model)
    def get(self):
        """Get comprehensive admission statistics"""
        pass

@admission_ns.route('/bulk-operations')
class AdmissionBulkAPI(Resource):
    @admission_ns.doc('bulk_admission_operations',
        description='''
        **Bulk Admission Operations (Admin Only)**
        
        Perform bulk operations on admission applications.
        
        **Access Control:** Admin only
        
        **Supported Operations:**
        - **import**: Import applications from external systems
        - **export**: Export applications data
        - **status_update**: Bulk status updates
        - **interview_schedule**: Bulk interview scheduling
        - **document_check**: Bulk document verification
        - **notification**: Send bulk notifications
        
        **Import Features:**
        - CSV/Excel format support
        - Data validation and error reporting
        - Duplicate detection and handling
        - Progress tracking for large batches
        
        **Export Options:**
        - Multiple file formats (CSV, Excel, PDF)
        - Custom field selection
        - Filtered data export
        - Automated report scheduling
        
        **Bulk Status Updates:**
        - Batch approval/rejection
        - Conditional updates based on criteria
        - Audit trail maintenance
        - Automatic notification handling
        ''',
        security='Bearer Auth')
    @admission_ns.response(200, 'Bulk operation completed successfully')
    @admission_ns.response(400, 'Validation errors in bulk data', error_model)
    @admission_ns.response(401, 'Authentication required', error_model)
    @admission_ns.response(403, 'Admin access required', error_model)
    def post(self):
        """Execute bulk operations on admissions"""
        pass
