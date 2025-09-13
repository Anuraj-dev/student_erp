import os
from app import create_app, socketio

# Create Flask app instance
app = create_app()

if __name__ == '__main__':
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("="*50)
    print("🎓 ERP Student Management System")
    print("🚀 Starting Flask Application with WebSocket support...")
    print(f"📍 Running on: http://localhost:{port}")
    print(f"🔧 Debug Mode: {debug}")
    print(f"🌍 Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print("📡 WebSocket Dashboard: /dashboard namespace")
    print("="*50)
    
    # Use socketio.run instead of app.run for WebSocket support
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug
    )