const express = require('express');
const fs = require('fs');
const path = require('path');
const { validateOutputFolder, validateEndpoints, ROUTE_CONFIG } = require('./validate-routes');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.static('public'));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    outputFolder: fs.existsSync(ROUTE_CONFIG.outputFolder)
  });
});

// Get all files in output folder
app.get('/api/files', (req, res) => {
  try {
    const files = fs.readdirSync(ROUTE_CONFIG.outputFolder)
      .filter(file => {
        const ext = path.extname(file);
        return ROUTE_CONFIG.allowedExtensions.includes(ext);
      })
      .map(file => {
        const filePath = path.join(ROUTE_CONFIG.outputFolder, file);
        const stats = fs.statSync(filePath);
        return {
          name: file,
          size: stats.size,
          modified: stats.mtime,
          extension: path.extname(file)
        };
      });
    
    res.json({ files, count: files.length });
  } catch (error) {
    res.status(500).json({ error: 'Failed to read output folder' });
  }
});

// Get specific file content
app.get('/api/files/:filename', (req, res) => {
  const { filename } = req.params;
  const filePath = path.join(ROUTE_CONFIG.outputFolder, filename);
  
  // Validate file extension
  const ext = path.extname(filename);
  if (!ROUTE_CONFIG.allowedExtensions.includes(ext)) {
    return res.status(400).json({ error: 'File type not allowed' });
  }
  
  // Check if file exists
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'File not found' });
  }
  
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    res.json({ filename, content, size: content.length });
  } catch (error) {
    res.status(500).json({ error: 'Failed to read file' });
  }
});

// Validate route configuration
app.get('/api/validate', (req, res) => {
  const folderValid = validateOutputFolder();
  
  res.json({
    outputFolder: {
      path: ROUTE_CONFIG.outputFolder,
      exists: fs.existsSync(ROUTE_CONFIG.outputFolder),
      valid: folderValid
    },
    config: ROUTE_CONFIG
  });
});

// Start server with validation
function startServer() {
  // Validate output folder before starting
  if (!validateOutputFolder()) {
    console.error('❌ Server startup failed: Output folder validation');
    process.exit(1);
  }
  
  app.listen(PORT, () => {
    console.log(`🚀 Server running on port ${PORT}`);
    console.log(`📁 Output folder: ${ROUTE_CONFIG.outputFolder}`);
    
    // Validate endpoints after server starts
    validateEndpoints(app);
    
    console.log('\n🌐 Available endpoints:');
    console.log(`  http://localhost:${PORT}/health`);
    console.log(`  http://localhost:${PORT}/api/files`);
    console.log(`  http://localhost:${PORT}/api/validate`);
  });
}

startServer();

module.exports = app;