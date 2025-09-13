#!/bin/bash

# ERP Student Management System - Test Runner
# Government of Rajasthan | Testing Framework

echo "🧪 ERP STUDENT MANAGEMENT SYSTEM - TEST RUNNER"
echo "=============================================="
echo "Government of Rajasthan | Backend Testing"
echo ""

# Change to parent directory for proper imports
cd "$(dirname "$0")/.."

echo "📍 Working Directory: $(pwd)"
echo "🐍 Python Version: $(python --version)"
echo ""

# Export PYTHONPATH to ensure imports work
export PYTHONPATH="$(pwd):$PYTHONPATH"

echo "🚀 RUNNING COMPREHENSIVE BACKEND TEST:"
echo "======================================"

# Run the comprehensive test
python tests/test_comprehensive_backend.py

echo ""
echo "✨ Test execution completed!"
echo "📁 To run individual tests, use: python tests/test_<name>.py from project root"
