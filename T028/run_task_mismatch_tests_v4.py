#!/usr/bin/env python3

import unittest
import sys
import json
from datetime import datetime

def run_validation_tests():
    """Run all task_mismatch validation tests and generate report"""
    
    # Test suite setup
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test modules
    try:
        from test_task_mismatch_v4 import TestTaskMismatchV4
        from integration_test_task_mismatch_v4 import TestTaskMismatchIntegrationV4
        
        suite.addTests(loader.loadTestsFromTestCase(TestTaskMismatchV4))
        suite.addTests(loader.loadTestsFromTestCase(TestTaskMismatchIntegrationV4))
    except ImportError as e:
        print(f"Warning: Could not import test module: {e}")
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Generate validation report
    report = {
        "timestamp": datetime.now().isoformat(),
        "version": "3.3.023",
        "test_type": "task_mismatch_validation_v4",
        "total_tests": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success_rate": (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100 if result.testsRun > 0 else 0,
        "status": "PASSED" if result.wasSuccessful() else "FAILED"
    }
    
    # Save report
    with open(f"task_mismatch_validation_v4_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n=== VALIDATION REPORT V4 ===")
    print(f"Tests run: {report['total_tests']}")
    print(f"Failures: {report['failures']}")
    print(f"Errors: {report['errors']}")
    print(f"Success rate: {report['success_rate']:.1f}%")
    print(f"Status: {report['status']}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_validation_tests()
    sys.exit(0 if success else 1)
