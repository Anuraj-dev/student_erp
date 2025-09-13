"""
Dashboard API Documentation
Comprehensive documentation for dashboard-related endpoints
"""

from flask_restx import Resource
from app.documentation import (
    dashboard_ns, dashboard_stats_model, dashboard_activity_model,
    success_model, error_model
)

@dashboard_ns.route('/stats')
class DashboardStatsAPI(Resource):
    @dashboard_ns.doc('get_dashboard_stats',
        description='''
        **Get Dashboard Statistics**
        
        Retrieve dashboard statistics based on user role.
        
        **Access Control:** All authenticated users (role-based data)
        
        **Admin Dashboard:**
        - Total students, staff, courses
        - Fee collection statistics
        - Admission pipeline status
        - System performance metrics
        - Recent activities overview
        
        **Student Dashboard:**
        - Personal academic summary
        - Fee payment status
        - Library book status
        - Hostel information
        - Upcoming deadlines
        
        **Staff Dashboard:**
        - Department statistics
        - Assigned tasks/responsibilities
        - Student performance metrics
        - Recent activities in their domain
        
        **Query Parameters:**
        - `period`: Time period for statistics (today, week, month, year)
        - `refresh`: Force refresh cached statistics
        ''',
        security='Bearer Auth')
    @dashboard_ns.marshal_with(dashboard_stats_model, code=200, description='Dashboard statistics retrieved')
    @dashboard_ns.response(401, 'Authentication required', error_model)
    def get(self):
        """Get role-based dashboard statistics"""
        pass

@dashboard_ns.route('/recent-activities')
class DashboardActivitiesAPI(Resource):
    @dashboard_ns.doc('get_recent_activities',
        description='''
        **Get Recent Activities**
        
        Retrieve recent activities relevant to the user.
        
        **Access Control:** All authenticated users (role-based filtering)
        
        **Activity Types:**
        - **Admin**: System-wide activities, major events
        - **Staff**: Department-specific activities, assigned tasks
        - **Students**: Personal activities, important updates
        
        **Query Parameters:**
        - `limit`: Maximum number of activities (default: 10, max: 50)
        - `activity_type`: Filter by activity type
        - `from_date`: Show activities from specific date
        ''',
        security='Bearer Auth')
    @dashboard_ns.marshal_list_with(dashboard_activity_model, code=200, description='Recent activities retrieved')
    @dashboard_ns.response(401, 'Authentication required', error_model)
    def get(self):
        """Get recent activities for user"""
        pass

@dashboard_ns.route('/notifications')
class DashboardNotificationsAPI(Resource):
    @dashboard_ns.doc('get_notifications',
        description='''
        **Get User Notifications**
        
        Retrieve notifications for the current user.
        
        **Access Control:** All authenticated users
        
        **Notification Types:**
        - **system**: System announcements
        - **academic**: Academic-related notifications
        - **fee**: Fee payment reminders and receipts
        - **library**: Library due dates and fines
        - **hostel**: Hostel-related notifications
        - **personal**: Personal messages and updates
        
        **Query Parameters:**
        - `unread_only`: Show only unread notifications
        - `type`: Filter by notification type
        - `limit`: Maximum number of notifications
        ''',
        security='Bearer Auth')
    @dashboard_ns.response(200, 'Notifications retrieved')
    @dashboard_ns.response(401, 'Authentication required', error_model)
    def get(self):
        """Get user notifications"""
        pass
