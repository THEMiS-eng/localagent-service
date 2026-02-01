#!/bin/bash

# Task Mismatch Validation Test v2
# Version: 3.3.021

set -e

echo "=== Task Mismatch Validation Test v2 ==="
echo "Version: 3.3.021"
echo "Date: $(date)"
echo

# Check if test files exist
if [ ! -f "test_task_mismatch_v2.json" ]; then
    echo "ERROR: test_task_mismatch_v2.json not found"
    exit 1
fi

if [ ! -f "run_task_mismatch_test_v2.py" ]; then
    echo "ERROR: run_task_mismatch_test_v2.py not found"
    exit 1
fi

# Make Python script executable
chmod +x run_task_mismatch_test_v2.py

echo "Running task_mismatch validation tests..."
echo

# Run the validation tests
if python3 run_task_mismatch_test_v2.py; then
    echo
    echo "✓ All task_mismatch validation tests passed!"
    echo "Task validation is working correctly."
    exit 0
else
    echo
    echo "✗ Some task_mismatch validation tests failed!"
    echo "Please check the validation logic."
    exit 1
fi