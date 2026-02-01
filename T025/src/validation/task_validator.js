// Task validation module
const VALID_TASK_TYPES = ['create_file', 'update_file', 'delete_file'];
const REQUIRED_FIELDS = ['id', 'type', 'description', 'filename', 'content'];

function validateTaskStructure(task) {
  // Check if task is an object
  if (typeof task !== 'object' || task === null) {
    return {
      valid: false,
      error: 'task_mismatch',
      details: 'Task must be an object'
    };
  }
  
  // Check required fields
  for (const field of REQUIRED_FIELDS) {
    if (!(field in task)) {
      return {
        valid: false,
        error: 'task_mismatch',
        details: `Missing required field: ${field}`
      };
    }
  }
  
  // Check valid task type
  if (!VALID_TASK_TYPES.includes(task.type)) {
    return {
      valid: false,
      error: 'task_mismatch',
      details: `Invalid task type: ${task.type}. Valid types: ${VALID_TASK_TYPES.join(', ')}`
    };
  }
  
  // Check content length (max 50 lines as per constraints)
  const lineCount = task.content.split('\n').length;
  if (lineCount > 50) {
    return {
      valid: false,
      error: 'task_mismatch',
      details: `Task content exceeds 50 lines: ${lineCount}`
    };
  }
  
  return { valid: true };
}

module.exports = { validateTaskStructure };