import unittest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.workflow.task_processor import TaskProcessor
from src.exceptions.task_exceptions import TaskMismatchError

class TestTaskMismatchIntegration(unittest.TestCase):
    def setUp(self):
        self.processor = TaskProcessor()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_full_workflow_task_mismatch(self):
        """Test complete workflow handles task mismatch properly"""
        request_data = {
            "tasks": [
                {"id": "T001", "type": "create_file", "filename": "test.py", "content": "print('test')"}
            ]
        }
        
        response_data = {
            "tasks": [
                {"id": "T002", "type": "create_file", "filename": "test.py", "content": "print('test')"}
            ]
        }
        
        with self.assertRaises(TaskMismatchError):
            self.processor.process_tasks(request_data, response_data)
            
    def test_partial_task_completion_with_mismatch(self):
        """Test workflow stops at first mismatch and reports progress"""
        request_data = {
            "tasks": [
                {"id": "T001", "type": "create_file", "filename": "valid.py", "content": "valid"},
                {"id": "T002", "type": "create_file", "filename": "test.py", "content": "test"}
            ]
        }
        
        response_data = {
            "tasks": [
                {"id": "T001", "type": "create_file", "filename": "valid.py", "content": "valid"},
                {"id": "T003", "type": "create_file", "filename": "test.py", "content": "test"}
            ]
        }
        
        with self.assertRaises(TaskMismatchError) as context:
            self.processor.process_tasks(request_data, response_data)
            
        self.assertIn("Task 1 completed successfully", str(context.exception))
        
    @patch('src.logging.task_logger')
    def test_mismatch_logging(self, mock_logger):
        """Test that task mismatches are properly logged"""
        request_data = {"tasks": [{"id": "T001", "type": "create_file"}]}
        response_data = {"tasks": [{"id": "T002", "type": "create_file"}]}
        
        try:
            self.processor.process_tasks(request_data, response_data)
        except TaskMismatchError:
            pass
            
        mock_logger.error.assert_called_once()

if __name__ == '__main__':
    unittest.main()