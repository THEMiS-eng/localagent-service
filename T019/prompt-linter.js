class PromptLinter {
    constructor() {
        this.rules = new Map();
        this.loadDefaultRules();
    }

    loadDefaultRules() {
        this.addRule('security', {
            name: 'Security Check',
            check: (prompt) => {
                const dangerous = ['eval', 'exec', 'system', 'shell'];
                return !dangerous.some(word => prompt.toLowerCase().includes(word));
            },
            message: 'Prompt contains potentially dangerous keywords'
        });

        this.addRule('length', {
            name: 'Length Check',
            check: (prompt) => prompt.length > 0 && prompt.length <= 5000,
            message: 'Prompt must be between 1-5000 characters'
        });

        this.addRule('injection', {
            name: 'Injection Prevention',
            check: (prompt) => {
                const patterns = [/<!--.*?-->/gs, /<script.*?>/gi, /javascript:/gi];
                return !patterns.some(pattern => pattern.test(prompt));
            },
            message: 'Prompt contains potential injection patterns'
        });
    }

    addRule(id, rule) {
        this.rules.set(id, rule);
    }

    removeRule(id) {
        return this.rules.delete(id);
    }

    lint(prompt) {
        const results = {
            valid: true,
            errors: [],
            warnings: [],
            info: { length: prompt.length, rules_checked: this.rules.size }
        };

        for (const [id, rule] of this.rules) {
            try {
                if (!rule.check(prompt)) {
                    results.valid = false;
                    results.errors.push({
                        rule: id,
                        name: rule.name,
                        message: rule.message
                    });
                }
            } catch (error) {
                results.warnings.push({
                    rule: id,
                    message: `Rule '${id}' failed to execute: ${error.message}`
                });
            }
        }

        return results;
    }
}

module.exports = PromptLinter;