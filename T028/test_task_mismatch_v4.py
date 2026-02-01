#!/usr/bin/env python3

import unittest
from unittest.mock import Mock, patch
import json

class TaskMismatchValidatorV4:
    def __init__(self):
        self.validation_rules = {
            'required_fields': ['id', 'type', 'description'],
            'max_tasks': 3,
            'max_lines': 50
        }
    
    def validate_task_structure(self, task):
        errors = []
        for field in self.validation_rules['required_fields']:
            if field not in task:
                errors.append(f"Missing required field: {field}")
        return errors
    
    def validate_task_limits(self, tasks):
        if len(tasks) > self.validation_rules['max_tasks']:
            return [f"Too many tasks: {len(tasks)} (max {self.validation_rules['max_tasks']})"]
        return []
    
    def validate_content_length(self, task):
        if 'content' in task:
            lines = task['content'].count('\n') + 1
            if lines > self.validation_rules['max_lines']:
                return [f"Task content too long: {lines} lines (max {self.validation_rules['max_lines']})"]
        return []

class TestTaskMismatchV4(unittest.TestCase):
    def setUp(self):
        self.validator = TaskMismatchValidatorV4()
    
    def test_valid_task_structure(self):
        task = {"id": "T001", "type": "create_file", "description": "Test"}
        errors = self.validator.validate_task_structure(task)
        self.assertEqual(errors, [])
    
    def test_missing_required_fields(self):
        task = {"id": "T001", "description": "Test"}
        errors = self.validator.validate_task_structure(task)
        self.assertIn("Missing required field: type", errors)
    
    def test_task_limit_exceeded(self):
        tasks = [{"id": f"T{i:03d}"} for i in range(5)]
        errors = self.validator.validate_task_limits(tasks)
        self.assertIn("Too many tasks: 5 (max 3)", errors)
    
    def test_content_length_validation(self):
        task = {"content": "\n".join(["line"] * 60)}
        errors = self.validator.validate_content_length(task)
        self.assertIn("Task content too long: 60 lines (max 50)", errors)

if __name__ == '__main__':
    unittest.main()
