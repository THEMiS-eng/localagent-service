/**
 * Task Mismatch Validator
 * Detects when tasks don't align between human requests and Claude responses
 */

class TaskMismatchValidator {
  constructor() {
    this.name = 'task_mismatch';
  }

  /**
   * Validate task alignment between request and response
   * @param {Object} context - Validation context
   * @returns {Object} Validation result
   */
  validate(context) {
    const { humanRequest, claudeResponse, expectedTasks } = context;
    
    if (!claudeResponse.tasks || claudeResponse.tasks.length === 0) {
      return {
        isValid: false,
        error: 'task_mismatch',
        message: 'No tasks found in response but tasks were expected',
        severity: 'high'
      };
    }

    // Check if response tasks match expected task types
    const responseTasks = claudeResponse.tasks.map(t => t.type);
    const expectedTypes = expectedTasks || this.inferExpectedTasks(humanRequest);
    
    if (expectedTypes.length > 0) {
      const hasMatchingTasks = expectedTypes.some(type => 
        responseTasks.includes(type)
      );
      
      if (!hasMatchingTasks) {
        return {
          isValid: false,
          error: 'task_mismatch',
          message: `Task types don't match. Expected: ${expectedTypes.join(', ')}, Got: ${responseTasks.join(', ')}`,
          severity: 'medium'
        };
      }
    }

    return {
      isValid: true,
      message: 'Task alignment validated successfully'
    };
  }

  /**
   * Infer expected task types from human request
   * @param {string} request - Human request text
   * @returns {Array} Expected task types
   */
  inferExpectedTasks(request) {
    const keywords = {
      'create_file': ['create', 'generate', 'make', 'build', 'add'],
      'modify_file': ['update', 'modify', 'change', 'edit', 'fix'],
      'delete_file': ['delete', 'remove', 'clear']
    };

    const expectedTypes = [];
    const lowerRequest = request.toLowerCase();

    for (const [taskType, words] of Object.entries(keywords)) {
      if (words.some(word => lowerRequest.includes(word))) {
        expectedTypes.push(taskType);
      }
    }

    return expectedTypes;
  }
}

module.exports = TaskMismatchValidator;