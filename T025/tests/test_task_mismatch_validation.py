import pytest
import json
from unittest.mock import Mock, patch
from src.validation.task_validator import TaskValidator
from src.exceptions import TaskMismatchError

class TestTaskMismatchValidation:
    def setup_method(self):
        self.validator = TaskValidator()
        
    def test_too_many_tasks_validation(self):
        """Test validation fails when too many tasks provided"""
        response = {
            "tasks": [
                {"id": "T001", "type": "create_file"},
                {"id": "T002", "type": "create_file"},
                {"id": "T003", "type": "create_file"},
                {"id": "T004", "type": "create_file"}
            ]
        }
        
        with pytest.raises(TaskMismatchError) as exc_info:
            self.validator.validate_task_count(response, max_tasks=3)
        
        assert "Too many tasks: 4 (max 3)" in str(exc_info.value)
        
    def test_no_tasks_validation(self):
        """Test validation fails when no tasks provided"""
        response = {"tasks": []}
        
        with pytest.raises(TaskMismatchError) as exc_info:
            self.validator.validate_task_count(response, min_tasks=1)
            
        assert "no_tasks" in str(exc_info.value)
        
    def test_valid_task_count(self):
        """Test validation passes with valid task count"""
        response = {
            "tasks": [
                {"id": "T001", "type": "create_file"},
                {"id": "T002", "type": "update_file"}
            ]
        }
        
        # Should not raise exception
        result = self.validator.validate_task_count(response, max_tasks=3)
        assert result is True
        
    def test_task_id_uniqueness(self):
        """Test validation fails with duplicate task IDs"""
        response = {
            "tasks": [
                {"id": "T001", "type": "create_file"},
                {"id": "T001", "type": "update_file"}
            ]
        }
        
        with pytest.raises(TaskMismatchError) as exc_info:
            self.validator.validate_task_ids(response)
            
        assert "duplicate task ID: T001" in str(exc_info.value).lower()