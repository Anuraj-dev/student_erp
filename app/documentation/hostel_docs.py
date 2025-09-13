"""
Hostel Management API Documentation
Comprehensive documentation for hostel-related endpoints
"""

from flask_restx import Resource
from app.documentation import (
    hostel_ns, hostel_model, hostel_room_model, hostel_allocation_model,
    success_model, error_model, pagination_model
)

@hostel_ns.route('')
class HostelsListAPI(Resource):
    @hostel_ns.doc('list_hostels',
        description='''
        **Get Hostels List**
        
        Retrieve list of all hostels with room availability.
        
        **Access Control:** All authenticated users
        
        **Includes:**
        - Hostel basic information
        - Room availability summary
        - Facilities and amenities
        - Current occupancy rates
        - Fee structure
        
        **Query Parameters:**
        - `gender`: Filter by gender (male, female, co-ed)
        - `available_only`: Show only hostels with available rooms
        - `include_facilities`: Include detailed facilities list
        ''',
        security='Bearer Auth')
    @hostel_ns.marshal_list_with(hostel_model, code=200, description='Hostels retrieved successfully')
    @hostel_ns.response(401, 'Authentication required', error_model)
    def get(self):
        """Get list of all hostels"""
        pass

@hostel_ns.route('/<int:hostel_id>/rooms')
class HostelRoomsAPI(Resource):
    @hostel_ns.doc('get_hostel_rooms',
        description='''
        **Get Hostel Rooms**
        
        Retrieve rooms for a specific hostel.
        
        **Access Control:**
        - **Admin/Staff**: Can view all rooms
        - **Students**: Can view available rooms only
        
        **Query Parameters:**
        - `available_only`: Show only available rooms
        - `room_type`: Filter by room type (single, double, triple)
        - `floor`: Filter by floor number
        ''',
        security='Bearer Auth')
    @hostel_ns.marshal_list_with(hostel_room_model, code=200, description='Rooms retrieved')
    @hostel_ns.response(401, 'Authentication required', error_model)
    @hostel_ns.response(404, 'Hostel not found', error_model)
    def get(self, hostel_id):
        """Get rooms for specific hostel"""
        pass

@hostel_ns.route('/allocations')
class HostelAllocationsAPI(Resource):
    @hostel_ns.doc('list_allocations',
        description='''
        **Get Hostel Allocations**
        
        Retrieve hostel room allocations.
        
        **Access Control:**
        - **Admin/Staff**: Can view all allocations
        - **Students**: Can view their own allocation only
        
        **Query Parameters:**
        - `student_roll`: Filter by student roll number
        - `hostel_id`: Filter by hostel
        - `status`: Filter by allocation status
        - `academic_year`: Filter by academic year
        ''',
        security='Bearer Auth')
    @hostel_ns.marshal_list_with(hostel_allocation_model, code=200, description='Allocations retrieved')
    @hostel_ns.response(401, 'Authentication required', error_model)
    def get(self):
        """Get hostel allocations"""
        pass

    @hostel_ns.doc('create_allocation',
        description='''
        **Create Hostel Allocation (Staff Only)**
        
        Allocate a room to a student.
        
        **Access Control:** Staff and Admin only
        
        **Process:**
        1. Validates student eligibility
        2. Checks room availability
        3. Creates allocation record
        4. Generates hostel fees
        5. Sends confirmation to student
        ''',
        security='Bearer Auth')
    @hostel_ns.expect(hostel_allocation_model, validate=True)
    @hostel_ns.marshal_with(hostel_allocation_model, code=201, description='Allocation created')
    @hostel_ns.response(400, 'Validation errors', error_model)
    @hostel_ns.response(401, 'Authentication required', error_model)
    @hostel_ns.response(403, 'Staff access required', error_model)
    @hostel_ns.response(409, 'Room not available or student already allocated', error_model)
    def post(self):
        """Create hostel allocation"""
        pass
