const fs = require('fs');
const path = require('path');
const express = require('express');

// Route validation configuration
const ROUTE_CONFIG = {
  outputFolder: './output',
  endpoints: [
    '/api/files',
    '/api/files/:filename',
    '/api/validate',
    '/health'
  ],
  allowedExtensions: ['.txt', '.json', '.html', '.css', '.js', '.md'],
  maxFileSize: 10 * 1024 * 1024 // 10MB
};

// Validate output folder structure
function validateOutputFolder() {
  const { outputFolder } = ROUTE_CONFIG;
  
  console.log('🔍 Validating output folder...');
  
  // Check if folder exists
  if (!fs.existsSync(outputFolder)) {
    console.log('📁 Creating output folder:', outputFolder);
    fs.mkdirSync(outputFolder, { recursive: true });
  }
  
  // Check permissions
  try {
    fs.accessSync(outputFolder, fs.constants.R_OK | fs.constants.W_OK);
    console.log('✅ Output folder permissions: OK');
  } catch (error) {
    console.error('❌ Output folder permissions: FAILED', error.message);
    return false;
  }
  
  return true;
}

// Validate endpoint routes
function validateEndpoints(app) {
  console.log('🔍 Validating endpoints...');
  
  const routes = [];
  
  // Extract routes from Express app
  app._router.stack.forEach(middleware => {
    if (middleware.route) {
      routes.push({
        path: middleware.route.path,
        methods: Object.keys(middleware.route.methods)
      });
    }
  });
  
  console.log('📋 Registered routes:');
  routes.forEach(route => {
    console.log(`  ${route.methods.join(', ').toUpperCase()} ${route.path}`);
  });
  
  // Validate expected endpoints
  ROUTE_CONFIG.endpoints.forEach(endpoint => {
    const found = routes.some(route => route.path === endpoint);
    if (found) {
      console.log(`✅ Endpoint ${endpoint}: OK`);
    } else {
      console.log(`❌ Endpoint ${endpoint}: MISSING`);
    }
  });
}

module.exports = {
  ROUTE_CONFIG,
  validateOutputFolder,
  validateEndpoints
};