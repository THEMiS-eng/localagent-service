import pytest
import json
from unittest.mock import Mock, patch
from src.handlers.request_handler import RequestHandler
from src.exceptions import TaskMismatchError

class TestTaskMismatchIntegration:
    def setup_method(self):
        self.handler = RequestHandler()
        
    @patch('src.handlers.request_handler.logger')
    def test_request_rejected_too_many_tasks(self, mock_logger):
        """Test complete request flow rejects excessive tasks"""
        request_data = {
            "message": "Create multiple files",
            "tasks": [
                {"id": "T001", "type": "create_file", "filename": "test1.py"},
                {"id": "T002", "type": "create_file", "filename": "test2.py"},
                {"id": "T003", "type": "create_file", "filename": "test3.py"},
                {"id": "T004", "type": "create_file", "filename": "test4.py"},
                {"id": "T005", "type": "create_file", "filename": "test5.py"}
            ]
        }
        
        with pytest.raises(TaskMismatchError):
            self.handler.process_request(request_data)
            
        mock_logger.error.assert_called()
        
    def test_empty_tasks_handling(self):
        """Test handling of requests with empty task lists"""
        request_data = {
            "message": "No tasks provided",
            "tasks": []
        }
        
        with pytest.raises(TaskMismatchError) as exc_info:
            self.handler.process_request(request_data)
            
        assert "no tasks" in str(exc_info.value).lower()
        
    def test_malformed_tasks_structure(self):
        """Test handling of malformed task structures"""
        request_data = {
            "message": "Malformed tasks",
            "tasks": [
                {"id": "T001"},  # Missing required fields
                {"type": "create_file"}  # Missing ID
            ]
        }
        
        with pytest.raises(TaskMismatchError):
            self.handler.validate_tasks(request_data)
            
    @patch('src.handlers.request_handler.TaskValidator')
    def test_validation_pipeline_integration(self, mock_validator):
        """Test complete validation pipeline integration"""
        mock_validator.return_value.validate_task_count.side_effect = TaskMismatchError("Test error")
        
        request_data = {
            "message": "Test request",
            "tasks": [{"id": "T001", "type": "create_file"}]
        }
        
        with pytest.raises(TaskMismatchError):
            self.handler.process_request(request_data)