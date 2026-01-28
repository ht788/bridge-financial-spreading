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
    // Check if backend is actually running (not just process object exists)
    const isRunning = backendProcess && !backendProcess.killed && backendProcess.exitCode === null;
    
    if (isRunning) {
      // Try a health check to verify it's really running
      const http = require('http');
      const healthCheck = http.get('http://localhost:8000/api/health', (healthRes) => {
        if (healthRes.statusCode === 200) {
          // Backend is truly running
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ 
            success: false, 
            message: 'Backend is already running and healthy' 
          }));
        } else {
          // Backend port responds but not healthy - restart it
          console.log('[Startup Service] Backend unhealthy, restarting...');
          if (backendProcess) backendProcess.kill();
          backendProcess = null;
          startBackend(res);
        }
      });
      
      healthCheck.on('error', () => {
        // Backend process exists but not responding - restart it
        console.log('[Startup Service] Backend not responding, restarting...');
        if (backendProcess) backendProcess.kill();
        backendProcess = null;
        startBackend(res);
      });
      
      healthCheck.setTimeout(2000);
      return;
    }
    
    // Backend not running, start it
    startBackend(res);
  } else if (req.url === '/restart' && req.method === 'POST') {
    // Force restart - kill existing process if any
    if (backendProcess) {
      console.log('[Startup Service] Killing existing backend process...');
      backendProcess.kill();
      backendProcess = null;
    }
    
    // Wait a moment for the process to fully terminate
    setTimeout(() => {
      startBackend(res);
    }, 1000);
  } else if (req.url === '/status' && req.method === 'GET') {
    const isRunning = backendProcess && !backendProcess.killed && backendProcess.exitCode === null;
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ 
      running: isRunning,
      exitCode: backendProcess ? backendProcess.exitCode : null
    }));
  } else {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});

function startBackend(res) {

  try {
    const backendPath = path.join(__dirname, 'backend', 'main.py');
    const isWindows = process.platform === 'win32';
    
    console.log('[Startup Service] Starting backend...');
    
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
}

server.listen(PORT, () => {
  console.log(`Backend startup service running on http://localhost:${PORT}`);
  console.log('POST /start - Start the backend server (or restart if unhealthy)');
  console.log('POST /restart - Force restart the backend server');
  console.log('GET /status - Check if backend is running');
});
