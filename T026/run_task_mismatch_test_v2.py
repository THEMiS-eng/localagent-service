#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def validate_task_structure(task):
    """Validate individual task structure"""
    required_fields = ['id', 'type', 'description', 'filename', 'content']
    valid_types = ['create_file', 'update_file', 'delete_file']
    
    # Check required fields
    for field in required_fields:
        if field not in task:
            return False, f"Missing required field: {field}"
    
    # Check task type
    if task['type'] not in valid_types:
        return False, f"Invalid task type: {task['type']}"
    
    # Check content not empty for create_file
    if task['type'] == 'create_file' and not task['content'].strip():
        return False, "Empty content for create_file task"
    
    return True, "Valid"

def run_validation_tests():
    """Run task_mismatch validation tests"""
    test_file = Path('test_task_mismatch_v2.json')
    
    if not test_file.exists():
        print("ERROR: Test configuration file not found")
        return False
    
    with open(test_file) as f:
        config = json.load(f)
    
    print(f"Running {config['test_name']} - Version {config['version']}")
    print("=" * 50)
    
    passed = 0
    total = len(config['scenarios'])
    
    for scenario in config['scenarios']:
        print(f"\nTest {scenario['id']}: {scenario['name']}")
        
        tasks = scenario['input']['tasks']
        expected_error = scenario['expected_error']
        
        # Validate each task
        task_errors = []
        for task in tasks:
            valid, error = validate_task_structure(task)
            if not valid:
                task_errors.append(error)
        
        # Check if we got expected error
        if task_errors and expected_error == 'task_mismatch':
            print(f"  ✓ PASS: Got expected error - {task_errors[0]}")
            passed += 1
        elif not task_errors and expected_error != 'task_mismatch':
            print(f"  ✓ PASS: No errors as expected")
            passed += 1
        else:
            print(f"  ✗ FAIL: Expected {expected_error}, got {task_errors}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    return passed == total

if __name__ == '__main__':
    success = run_validation_tests()
    sys.exit(0 if success else 1)