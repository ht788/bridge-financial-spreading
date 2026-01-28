/**
 * Simple HTTP service to start the backend server
 * Runs on port 8001 and can spawn the Python backend process
 */

const http = require('http');
const { spawn } = require('child_process');
const path = require('path');

const PORT = 8001;
let backendProcess = null;

const server = http.createServer((req, res) => {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  if (req.url === '/start' && req.method === 'POST') {
    // Check if backend is already running
    if (backendProcess && !backendProcess.killed) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ 
        success: false, 
        message: 'Backend is already starting or running' 
      }));
      return;
    }

    try {
      const backendPath = path.join(__dirname, 'backend', 'main.py');
      const isWindows = process.platform === 'win32';
      
      // Spawn the backend process
      if (isWindows) {
        backendProcess = spawn('python', [backendPath], {
          cwd: __dirname,
          detached: false,
          stdio: 'pipe'
        });
      } else {
        backendProcess = spawn('python3', [backendPath], {
          cwd: __dirname,
          detached: false,
          stdio: 'pipe'
        });
      }

      backendProcess.stdout.on('data', (data) => {
        console.log(`[Backend] ${data}`);
      });

      backendProcess.stderr.on('data', (data) => {
        console.error(`[Backend Error] ${data}`);
      });

      backendProcess.on('exit', (code) => {
        console.log(`[Backend] Process exited with code ${code}`);
        backendProcess = null;
      });

      backendProcess.on('error', (err) => {
        console.error(`[Backend] Failed to start: ${err.message}`);
        backendProcess = null;
      });

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ 
        success: true, 
        message: 'Backend startup initiated' 
      }));
    } catch (error) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ 
        success: false, 
        message: `Failed to start backend: ${error.message}` 
      }));
    }
  } else if (req.url === '/status' && req.method === 'GET') {
    const isRunning = backendProcess && !backendProcess.killed;
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ 
      running: isRunning 
    }));
  } else {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});

server.listen(PORT, () => {
  console.log(`Backend startup service running on http://localhost:${PORT}`);
  console.log('POST /start - Start the backend server');
  console.log('GET /status - Check if backend is starting');
});
