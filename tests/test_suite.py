"""
Test Suite Index - ERP Student Management System
This file provides an overview of all available tests and how to run them.
"""

import os
import sys
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def display_test_suite_info():
    """Display information about available tests"""
    print("🧪 ERP STUDENT MANAGEMENT SYSTEM - TEST SUITE")
    print("=" * 60)
    print("Government of Rajasthan | Backend Testing Framework")
    print()
    
    test_files = {
        "test_comprehensive_backend.py": {
            "description": "Complete backend verification (Tasks 1-10)",
            "purpose": "Main integration test for all backend components",
            "usage": "python test_comprehensive_backend.py"
        },
        "test_models.py": {
            "description": "Database models and relationships testing",
            "purpose": "Validates all SQLAlchemy models and constraints", 
            "usage": "python test_models.py"
        },
        "test_auth.py": {
            "description": "Authentication and authorization testing",
            "purpose": "JWT tokens, login, role-based access control",
            "usage": "python test_auth.py"
        },
        "test_admission.py": {
            "description": "Admission workflow and application processing",
            "purpose": "Complete admission lifecycle testing",
            "usage": "python test_admission.py"
        },
        "test_automated_services.py": {
            "description": "PDF generation and email services testing",
            "purpose": "Validates Task 10 automated services",
            "usage": "python test_automated_services.py"
        },
        "test_dashboard_complete.py": {
            "description": "Dashboard APIs and real-time analytics",
            "purpose": "WebSocket, charts, and dashboard endpoints",
            "usage": "python test_dashboard_complete.py"
        },
        "test_data_security_validation.py": {
            "description": "Security validation and input sanitization",
            "purpose": "Security measures and data protection",
            "usage": "python test_data_security_validation.py"
        },
        "test_library_management.py": {
            "description": "Library book issue/return system",
            "purpose": "Library module functionality testing",
            "usage": "python test_library_management.py"
        },
        "test_fee_management.py": {
            "description": "Fee payment and receipt generation",
            "purpose": "Financial operations testing",
            "usage": "python test_fee_management.py"
        },
        "test_hostel_management.py": {
            "description": "Hostel allocation and management",
            "purpose": "Hostel operations testing",
            "usage": "python test_hostel_management.py"
        },
        "security_demonstration.py": {
            "description": "Security features demonstration",
            "purpose": "Shows implemented security measures",
            "usage": "python security_demonstration.py"
        }
    }
    
    print("📋 AVAILABLE TEST FILES:")
    print("-" * 60)
    
    for filename, info in test_files.items():
        if os.path.exists(filename):
            status = "✅ Available"
        else:
            status = "❌ Missing"
            
        print(f"{status} {filename}")
        print(f"   📝 {info['description']}")
        print(f"   🎯 Purpose: {info['purpose']}")
        print(f"   🚀 Usage: {info['usage']}")
        print()
    
    print("🏃 QUICK RUN COMMANDS:")
    print("-" * 60)
    print("# Run comprehensive backend test (recommended)")
    print("python test_comprehensive_backend.py")
    print()
    print("# Run all tests using pytest")
    print("pytest")
    print()
    print("# Run specific test category")
    print("pytest test_models.py -v")
    print()
    print("# Run tests with coverage")
    print("pytest --cov=app --cov-report=html")
    print()

def run_all_tests():
    """Run all available tests"""
    test_files = [
        "test_comprehensive_backend.py",
        "test_models.py",
        "test_auth.py", 
        "test_admission.py",
        "test_automated_services.py"
    ]
    
    print("🚀 RUNNING ALL TESTS...")
    print("=" * 50)
    
    results = {}
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n📋 Running {test_file}...")
            try:
                result = subprocess.run(['python', test_file], 
                                     capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    results[test_file] = "✅ PASSED"
                else:
                    results[test_file] = "❌ FAILED"
            except subprocess.TimeoutExpired:
                results[test_file] = "⏰ TIMEOUT"
            except Exception as e:
                results[test_file] = f"❌ ERROR: {str(e)}"
        else:
            results[test_file] = "❌ FILE NOT FOUND"
    
    print("\n" + "=" * 50)
    print("🎯 TEST RESULTS SUMMARY:")
    print("-" * 50)
    
    for test_file, result in results.items():
        print(f"{result} - {test_file}")
    
    passed = sum(1 for r in results.values() if "PASSED" in r)
    total = len(results)
    success_rate = (passed / total) * 100
    
    print(f"\n📊 OVERALL: {passed}/{total} tests passed ({success_rate:.1f}%)")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run-all":
        run_all_tests()
    else:
        display_test_suite_info()
