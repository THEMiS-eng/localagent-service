const assert = require('assert');
const { validateTask } = require('../src/task_validator');

// Test suite for task_mismatch validation v3
describe('Task Mismatch Validation v3', () => {
  
  it('should reject invalid task type', () => {
    const invalidTask = {
      id: 'T001',
      type: 'invalid_type',
      description: 'Test task',
      filename: 'test.js',
      content: 'console.log("test");'
    };
    
    const result = validateTask(invalidTask);
    assert.strictEqual(result.valid, false);
    assert.strictEqual(result.error, 'task_mismatch');
  });
  
  it('should reject missing required fields', () => {
    const incompleteTask = {
      id: 'T002',
      type: 'create_file'
      // Missing description, filename, content
    };
    
    const result = validateTask(incompleteTask);
    assert.strictEqual(result.valid, false);
    assert.strictEqual(result.error, 'task_mismatch');
  });
  
  it('should accept valid create_file task', () => {
    const validTask = {
      id: 'T003',
      type: 'create_file',
      description: 'Valid test file',
      filename: 'valid.js',
      content: 'const test = true;'
    };
    
    const result = validateTask(validTask);
    assert.strictEqual(result.valid, true);
  });
  
  it('should reject malformed task structure', () => {
    const malformedTask = {
      id: 'T004',
      type: 'create_file',
      description: null,
      filename: '',
      content: undefined
    };
    
    const result = validateTask(malformedTask);
    assert.strictEqual(result.valid, false);
    assert.strictEqual(result.error, 'task_mismatch');
  });
});