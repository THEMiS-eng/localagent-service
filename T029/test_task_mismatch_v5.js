// Test suite for task_mismatch validation v5
// Version: 3.3.024

const { validateTaskMatch } = require('./task_validator');
const assert = require('assert');

describe('Task Mismatch Validation v5', () => {
  
  test('should detect task ID mismatch', () => {
    const requestedTasks = [{ id: 'T001', type: 'create_file' }];
    const responseTasks = [{ id: 'T002', type: 'create_file' }];
    
    const result = validateTaskMatch(requestedTasks, responseTasks);
    
    assert.strictEqual(result.valid, false);
    assert.strictEqual(result.error, 'task_mismatch');
    assert.strictEqual(result.details.mismatchedIds.length, 1);
  });
  
  test('should detect missing tasks', () => {
    const requestedTasks = [
      { id: 'T001', type: 'create_file' },
      { id: 'T002', type: 'update_file' }
    ];
    const responseTasks = [{ id: 'T001', type: 'create_file' }];
    
    const result = validateTaskMatch(requestedTasks, responseTasks);
    
    assert.strictEqual(result.valid, false);
    assert.strictEqual(result.error, 'missing_tasks');
    assert.deepStrictEqual(result.details.missingIds, ['T002']);
  });
  
  test('should validate matching tasks successfully', () => {
    const requestedTasks = [
      { id: 'T001', type: 'create_file' },
      { id: 'T002', type: 'update_file' }
    ];
    const responseTasks = [
      { id: 'T001', type: 'create_file' },
      { id: 'T002', type: 'update_file' }
    ];
    
    const result = validateTaskMatch(requestedTasks, responseTasks);
    
    assert.strictEqual(result.valid, true);
    assert.strictEqual(result.error, null);
  });
  
  test('should handle empty task arrays', () => {
    const result = validateTaskMatch([], []);
    
    assert.strictEqual(result.valid, true);
    assert.strictEqual(result.error, null);
  });
  
});

console.log('Task mismatch validation v5 tests completed');