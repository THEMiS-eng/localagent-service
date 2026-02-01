#!/usr/bin/env node

// Simple test runner for task mismatch validation
const { validateTaskStructure } = require('./src/validation/task_validator');

console.log('Running Task Mismatch Validation Tests...');

// Test cases
const testCases = [
  {
    name: 'Invalid task type',
    task: { id: 'T001', type: 'bad_type', description: 'Test', filename: 'test.js', content: 'test' },
    expected: false
  },
  {
    name: 'Missing fields',
    task: { id: 'T002', type: 'create_file' },
    expected: false
  },
  {
    name: 'Valid task',
    task: { id: 'T003', type: 'create_file', description: 'Test', filename: 'test.js', content: 'console.log("test");' },
    expected: true
  },
  {
    name: 'Non-object task',
    task: 'invalid',
    expected: false
  }
];

let passed = 0;
let failed = 0;

testCases.forEach(testCase => {
  const result = validateTaskStructure(testCase.task);
  const success = result.valid === testCase.expected;
  
  console.log(`${success ? '✓' : '✗'} ${testCase.name}`);
  if (!success) {
    console.log(`  Expected: ${testCase.expected}, Got: ${result.valid}`);
    if (result.error) console.log(`  Error: ${result.error} - ${result.details}`);
    failed++;
  } else {
    passed++;
  }
});

console.log(`\nResults: ${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);