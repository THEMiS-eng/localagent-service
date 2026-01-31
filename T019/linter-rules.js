const RULE_CATEGORIES = {
    SECURITY: 'security',
    CONTENT: 'content',
    FORMAT: 'format',
    PERFORMANCE: 'performance'
};

const DEFAULT_RULES = {
    // Security Rules
    no_code_execution: {
        category: RULE_CATEGORIES.SECURITY,
        name: 'No Code Execution',
        severity: 'error',
        check: (prompt) => {
            const codePatterns = [
                /exec\s*\(/gi,
                /eval\s*\(/gi,
                /system\s*\(/gi,
                /\$\{.*\}/g,
                /`.*`/g
            ];
            return !codePatterns.some(pattern => pattern.test(prompt));
        },
        message: 'Prompt contains code execution patterns'
    },

    // Content Rules
    no_empty_prompt: {
        category: RULE_CATEGORIES.CONTENT,
        name: 'No Empty Prompt',
        severity: 'error',
        check: (prompt) => prompt.trim().length > 0,
        message: 'Prompt cannot be empty'
    },

    max_tokens: {
        category: RULE_CATEGORIES.PERFORMANCE,
        name: 'Token Limit',
        severity: 'warning',
        check: (prompt) => {
            // Rough token estimation: 1 token ≈ 4 characters
            const estimatedTokens = Math.ceil(prompt.length / 4);
            return estimatedTokens <= 4000;
        },
        message: 'Prompt may exceed token limits'
    },

    // Format Rules
    valid_encoding: {
        category: RULE_CATEGORIES.FORMAT,
        name: 'Valid Encoding',
        severity: 'error',
        check: (prompt) => {
            try {
                // Check for valid UTF-8
                const encoded = encodeURIComponent(prompt);
                const decoded = decodeURIComponent(encoded);
                return decoded === prompt;
            } catch {
                return false;
            }
        },
        message: 'Prompt contains invalid character encoding'
    }
};

module.exports = {
    RULE_CATEGORIES,
    DEFAULT_RULES
};