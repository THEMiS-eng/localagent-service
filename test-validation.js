const axios = require('axios');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://localhost:3000';
const TEST_FILE = 'test-output.txt';

// Test suite for route validation
class RouteValidator {
  constructor() {
    this.passed = 0;
    this.failed = 0;
    this.results = [];
  }
  
  async test(name, testFn) {
    try {
      console.log(`🧪 Testing: ${name}`);
      await testFn();
      console.log(`✅ ${name}: PASSED`);
      this.passed++;
      this.results.push({ name, status: 'PASSED' });
    } catch (error) {
      console.log(`❌ ${name}: FAILED - ${error.message}`);
      this.failed++;
      this.results.push({ name, status: 'FAILED', error: error.message });
    }
  }
  
  async validateHealthEndpoint() {
    const response = await axios.get(`${BASE_URL}/health`);
    if (response.status !== 200) throw new Error('Health check failed');
    if (!response.data.status) throw new Error('Health status missing');
  }
  
  async validateFilesEndpoint() {
    const response = await axios.get(`${BASE_URL}/api/files`);
    if (response.status !== 200) throw new Error('Files endpoint failed');
    if (!Array.isArray(response.data.files)) throw new Error('Files array missing');
  }
  
  async validateSpecificFileEndpoint() {
    // Create test file first
    const outputDir = './output';
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    
    const testContent = 'Test file content for validation';
    fs.writeFileSync(path.join(outputDir, TEST_FILE), testContent);
    
    const response = await axios.get(`${BASE_URL}/api/files/${TEST_FILE}`);
    if (response.status !== 200) throw new Error('File endpoint failed');
    if (response.data.content !== testContent) throw new Error('File content mismatch');
    
    // Cleanup
    fs.unlinkSync(path.join(outputDir, TEST_FILE));
  }
  
  async validateNotFound() {
    try {
      await axios.get(`${BASE_URL}/api/files/nonexistent.txt`);
      throw new Error('Should have returned 404');
    } catch (error) {
      if (error.response && error.response.status === 404) {
        return; // Expected 404
      }
      throw error;
    }
  }
  
  async validateConfigEndpoint() {
    const response = await axios.get(`${BASE_URL}/api/validate`);
    if (response.status !== 200) throw new Error('Validate endpoint failed');
    if (!response.data.outputFolder) throw new Error('Output folder config missing');
    if (!response.data.config) throw new Error('Route config missing');
  }
  
  async runAllTests() {
    console.log('🚀 Starting route validation tests...\n');
    
    await this.test('Health Endpoint', () => this.validateHealthEndpoint());
    await this.test('Files Endpoint', () => this.validateFilesEndpoint());
    await this.test('Specific File Endpoint', () => this.validateSpecificFileEndpoint());
    await this.test('404 Not Found', () => this.validateNotFound());
    await this.test('Config Validation Endpoint', () => this.validateConfigEndpoint());
    
    console.log('\n📊 Test Results:');
    console.log(`✅ Passed: ${this.passed}`);
    console.log(`❌ Failed: ${this.failed}`);
    console.log(`📈 Success Rate: ${((this.passed / (this.passed + this.failed)) * 100).toFixed(1)}%`);
    
    if (this.failed > 0) {
      console.log('\n🔍 Failed Tests:');
      this.results.filter(r => r.status === 'FAILED').forEach(result => {
        console.log(`  - ${result.name}: ${result.error}`);
      });
    }
    
    return this.failed === 0;
  }
}

// Run tests if server is available
async function main() {
  try {
    // Check if server is running
    await axios.get(`${BASE_URL}/health`, { timeout: 5000 });
    
    const validator = new RouteValidator();
    const success = await validator.runAllTests();
    
    process.exit(success ? 0 : 1);
  } catch (error) {
    console.error('❌ Server not available. Start server first with: node server.js');
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = RouteValidator;