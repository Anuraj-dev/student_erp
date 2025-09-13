#!/usr/bin/env python3
"""
Quick Authentication Test Script
Tests the Flask app and authentication routes
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '/home/anuraj-dev/Anuraj-dev/Coding test/ERP_Colllege/student_erp')

def test_app_creation():
    """Test if Flask app can be created successfully"""
    try:
        from app import create_app
        
        print("🧪 Testing Flask App Creation...")
        app = create_app('testing')
        
        with app.app_context():
            print("✅ Flask app created successfully!")
            print(f"📍 App name: {app.name}")
            print(f"🔧 Config loaded: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
            print(f"🔑 JWT configured: {'JWT_SECRET_KEY' in app.config}")
            
            # Test blueprint registration
            print("\n📋 Registered Blueprints:")
            for name, blueprint in app.blueprints.items():
                print(f"  - {name}: {blueprint.url_prefix}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating Flask app: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_models():
    """Test if database models can be imported"""
    try:
        print("\n🗄️ Testing Database Models...")
        
        from app.models import (
            Student, Staff, Course, Hostel,
            AdmissionApplication, Fee, Library, Examination
        )
        
        print("✅ All database models imported successfully!")
        
        # Test model creation (without database)
        print("📊 Model classes loaded:")
        models = [Student, Staff, Course, Hostel, AdmissionApplication, Fee, Library, Examination]
        for model in models:
            print(f"  - {model.__name__}: {model.__tablename__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error importing models: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_auth_routes():
    """Test if authentication routes are accessible"""
    try:
        print("\n🔐 Testing Authentication Routes...")
        
        from app import create_app
        app = create_app('testing')
        
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/api/auth/health')
            print(f"Health check status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                print("✅ Auth routes are accessible!")
                print(f"📋 Available endpoints: {len(data.get('endpoints', []))}")
                for endpoint in data.get('endpoints', []):
                    print(f"  - {endpoint}")
            else:
                print(f"❌ Auth health check failed: {response.status_code}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing auth routes: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Starting ERP Authentication System Tests")
    print("=" * 50)
    
    tests = [
        ("Flask App Creation", test_app_creation),
        ("Database Models", test_database_models), 
        ("Authentication Routes", test_auth_routes)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            failed += 1
            print(f"❌ {test_name}: FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Authentication system is ready.")
        print("\n🚀 Next steps:")
        print("  1. Start the Flask server: python run.py")
        print("  2. Test login endpoint: POST /api/auth/login")
        print("  3. Proceed with Task 4: Admission Workflow")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
