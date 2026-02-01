import unittest
from unittest.mock import Mock, patch
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.validators.task_validator import TaskValidator
from src.exceptions.task_exceptions import TaskMismatchError

class TestTaskMismatchValidation(unittest.TestCase):
    def setUp(self):
        self.validator = TaskValidator()
        
    def test_valid_task_match(self):
        """Test that matching tasks pass validation"""
        expected_task = {'id': 'T001', 'type': 'create_file', 'filename': 'test.py'}
        actual_task = {'id': 'T001', 'type': 'create_file', 'filename': 'test.py'}
        
        result = self.validator.validate_task_match(expected_task, actual_task)
        self.assertTrue(result)
        
    def test_task_id_mismatch(self):
        """Test that mismatched task IDs raise TaskMismatchError"""
        expected_task = {'id': 'T001', 'type': 'create_file', 'filename': 'test.py'}
        actual_task = {'id': 'T002', 'type': 'create_file', 'filename': 'test.py'}
        
        with self.assertRaises(TaskMismatchError) as context:
            self.validator.validate_task_match(expected_task, actual_task)
        
        self.assertIn('Task ID mismatch', str(context.exception))
        
    def test_task_type_mismatch(self):
        """Test that mismatched task types raise TaskMismatchError"""
        expected_task = {'id': 'T001', 'type': 'create_file', 'filename': 'test.py'}
        actual_task = {'id': 'T001', 'type': 'update_file', 'filename': 'test.py'}
        
        with self.assertRaises(TaskMismatchError) as context:
            self.validator.validate_task_match(expected_task, actual_task)
        
        self.assertIn('Task type mismatch', str(context.exception))
        
    def test_filename_mismatch(self):
        """Test that mismatched filenames raise TaskMismatchError"""
        expected_task = {'id': 'T001', 'type': 'create_file', 'filename': 'test.py'}
        actual_task = {'id': 'T001', 'type': 'create_file', 'filename': 'other.py'}
        
        with self.assertRaises(TaskMismatchError) as context:
            self.validator.validate_task_match(expected_task, actual_task)
        
        self.assertIn('Filename mismatch', str(context.exception))

if __name__ == '__main__':
    unittest.main()