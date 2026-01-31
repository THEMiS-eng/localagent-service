#!/usr/bin/env node

const PromptLinter = require('./prompt-linter');
const { DEFAULT_RULES } = require('./linter-rules');
const fs = require('fs');
const path = require('path');

class PromptLinterCLI {
    constructor() {
        this.linter = new PromptLinter();
        this.loadCustomRules();
    }

    loadCustomRules() {
        // Load additional rules from DEFAULT_RULES
        Object.entries(DEFAULT_RULES).forEach(([id, rule]) => {
            this.linter.addRule(id, rule);
        });
    }

    async lintFile(filepath) {
        try {
            const content = fs.readFileSync(filepath, 'utf8');
            const results = this.linter.lint(content);
            this.printResults(filepath, results);
            return results.valid;
        } catch (error) {
            console.error(`Error reading file ${filepath}:`, error.message);
            return false;
        }
    }

    lintString(prompt) {
        const results = this.linter.lint(prompt);
        this.printResults('<string>', results);
        return results.valid;
    }

    printResults(source, results) {
        console.log(`\n📝 Linting: ${source}`);
        console.log(`Length: ${results.info.length} chars, Rules: ${results.info.rules_checked}`);
        
        if (results.valid) {
            console.log('✅ All checks passed!');
        } else {
            console.log('❌ Issues found:');
            results.errors.forEach(error => {
                console.log(`  - [${error.rule}] ${error.message}`);
            });
        }
        
        if (results.warnings.length > 0) {
            console.log('⚠️  Warnings:');
            results.warnings.forEach(warning => {
                console.log(`  - ${warning.message}`);
            });
        }
    }

    run() {
        const args = process.argv.slice(2);
        
        if (args.length === 0) {
            console.log('Usage: node lint-cli.js <file|string>');
            console.log('Example: node lint-cli.js prompt.txt');
            console.log('Example: node lint-cli.js "Hello world"');
            return;
        }

        const input = args[0];
        
        if (fs.existsSync(input)) {
            this.lintFile(input);
        } else {
            this.lintString(input);
        }
    }
}

if (require.main === module) {
    new PromptLinterCLI().run();
}

module.exports = PromptLinterCLI;