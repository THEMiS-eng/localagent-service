#!/usr/bin/env python3

import unittest
import json
from unittest.mock import patch, MagicMock

class TaskMismatchIntegrationV4:
    def __init__(self, config=None):
        self.config = config or {
            'validation_enabled': True,
            'strict_mode': False,
            'log_level': 'INFO'
        }
        self.errors = []
    
    def process_request(self, request_data):
        try:
            if not isinstance(request_data, dict):
                raise ValueError("Request must be a dictionary")
            
            if 'tasks' not in request_data:
                self.errors.append("no_tasks: Response contains no tasks")
                return False
            
            tasks = request_data['tasks']
            if len(tasks) > 3:
                self.errors.append(f"too_many_tasks: Too many tasks: {len(tasks)} (max 3)")
                return False
            
            for task in tasks:
                if self._validate_task_content(task):
                    continue
                return False
            
            return True
        except Exception as e:
            self.errors.append(f"parse_error: {str(e)}")
            return False
    
    def _validate_task_content(self, task):
        if 'content' in task and len(task['content']) > 2000:
            truncated_end = task['content'][-50:]
            self.errors.append(f"truncation: Response truncated, ends with: ...{truncated_end}")
            return False
        return True

class TestTaskMismatchIntegrationV4(unittest.TestCase):
    def setUp(self):
        self.processor = TaskMismatchIntegrationV4()
    
    def test_valid_request_processing(self):
        request = {
            "message": "Test message",
            "tasks": [
                {"id": "T001", "type": "create_file", "description": "Test", "content": "short"}
            ]
        }
        result = self.processor.process_request(request)
        self.assertTrue(result)
        self.assertEqual(self.processor.errors, [])
    
    def test_no_tasks_error(self):
        request = {"message": "Test message"}
        result = self.processor.process_request(request)
        self.assertFalse(result)
        self.assertIn("no_tasks: Response contains no tasks", self.processor.errors)
    
    def test_too_many_tasks_error(self):
        request = {
            "message": "Test",
            "tasks": [{"id": f"T{i:03d}"} for i in range(5)]
        }
        result = self.processor.process_request(request)
        self.assertFalse(result)
        self.assertTrue(any("too_many_tasks" in error for error in self.processor.errors))

if __name__ == '__main__':
    unittest.main()
