const assert = require('assert');
const { validateTaskStructure } = require('../src/validation/task_validator');

// Test task_mismatch validation scenarios
describe('Task Mismatch Validation', () => {
  
  it('should reject invalid task type', () => {
    const invalidTask = {
      id: 'T001',
      type: 'invalid_type',
      description: 'Test task',
      filename: 'test.js',
      content: 'console.log("test");'
    };
    
    const result = validateTaskStructure(invalidTask);
    assert.strictEqual(result.valid, false);
    assert.strictEqual(result.error, 'task_mismatch');
    assert(result.details.includes('invalid task type'));
  });
  
  it('should reject missing required fields', () => {
    const incompleteTask = {
      id: 'T002',
      type: 'create_file'
      // Missing description, filename, content
    };
    
    const result = validateTaskStructure(incompleteTask);
    assert.strictEqual(result.valid, false);
    assert.strictEqual(result.error, 'task_mismatch');
  });
  
  it('should reject malformed task structure', () => {
    const malformedTask = 'not_an_object';
    
    const result = validateTaskStructure(malformedTask);
    assert.strictEqual(result.valid, false);
    assert.strictEqual(result.error, 'task_mismatch');
  });
  
  it('should accept valid task structure', () => {
    const validTask = {
      id: 'T003',
      type: 'create_file',
      description: 'Valid test task',
      filename: 'valid.js',
      content: 'console.log("valid");'
    };
    
    const result = validateTaskStructure(validTask);
    assert.strictEqual(result.valid, true);
  });
});