import json
from typing import Dict, List, Any

class TaskMismatchFixtures:
    """Test fixtures for task mismatch validation scenarios"""
    
    @staticmethod
    def valid_single_task() -> Dict[str, Any]:
        """Returns valid single task request"""
        return {
            "message": "Create one file",
            "tasks": [
                {
                    "id": "T001",
                    "type": "create_file",
                    "description": "Test file",
                    "filename": "test.py",
                    "content": "print('hello')"
                }
            ]
        }
    
    @staticmethod
    def excessive_tasks_request() -> Dict[str, Any]:
        """Returns request with too many tasks (>3)"""
        tasks = []
        for i in range(1, 6):  # Creates 5 tasks
            tasks.append({
                "id": f"T{i:03d}",
                "type": "create_file",
                "description": f"Test file {i}",
                "filename": f"test{i}.py",
                "content": f"print('test {i}')"
            })
        
        return {
            "message": "Create multiple files",
            "tasks": tasks
        }
    
    @staticmethod
    def empty_tasks_request() -> Dict[str, Any]:
        """Returns request with empty task list"""
        return {
            "message": "No tasks to perform",
            "tasks": []
        }
    
    @staticmethod
    def duplicate_task_ids() -> Dict[str, Any]:
        """Returns request with duplicate task IDs"""
        return {
            "message": "Duplicate task IDs",
            "tasks": [
                {"id": "T001", "type": "create_file", "filename": "test1.py"},
                {"id": "T001", "type": "update_file", "filename": "test2.py"}
            ]
        }
    
    @staticmethod
    def malformed_tasks() -> List[Dict[str, Any]]:
        """Returns list of malformed task scenarios"""
        return [
            {"type": "create_file"},  # Missing ID
            {"id": "T002"},  # Missing type
            {"id": "T003", "type": "invalid_type"},  # Invalid type
            {}  # Completely empty
        ]