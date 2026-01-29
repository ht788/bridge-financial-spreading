# 🔧 Render Deployment - Potential Issues & Solutions

This document covers all potential issues you might encounter during Render deployment.

## ✅ Issues Already Fixed

1. **Build Script** - Created `build.sh` for proper dependency installation
2. **Python Runtime** - Explicitly specified Python 3.11.0
3. **Route Order** - Fixed static file serving to not conflict with API routes
4. **Port Handling** - Backend reads Render's PORT environment variable

---

## ⚠️ Potential Issues to Watch For

### 1. Build Timeout (Most Common)

**Problem:** Build takes longer than 15 minutes on free tier

**Symptoms:**
```
==> Build exceeded maximum duration of 15 minutes
```

**Solutions:**
- Upgrade to Starter plan ($7/month) - 30 min timeout
- OR reduce dependencies in requirements.txt
- OR use pre-built wheels

**Prevention:** The build should take 5-10 minutes normally

---

### 2. Memory Issues During Build

**Problem:** Not enough memory to build frontend

**Symptoms:**
```
FATAL ERROR: Reached heap limit
npm run build failed
```

**Solutions:**
- Upgrade to Starter plan (1GB RAM vs 512MB free)
- OR add to `build.sh`:
  ```bash
  export NODE_OPTIONS="--max-old-space-size=512"
  ```

---

### 3. Missing Environment Variables

**Problem:** API keys not set

**Symptoms:**
```
WARNING: No AI API keys set - spreading will fail!
```

**Solution:**
In Render dashboard → Environment → Add:
```
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=lsv2_pt_...
```

**Critical:** At least ONE of Anthropic or OpenAI must be set!

---

### 4. Frontend Build Fails

**Problem:** npm ci fails or build errors

**Symptoms:**
```
npm ERR! code ENOENT
npm run build failed
```

**Solutions:**
1. Check `frontend/package-lock.json` is committed
2. Verify Node version compatibility
3. Check for missing dependencies

**Fix:** The build.sh uses `npm ci` which requires package-lock.json

---

### 5. Static Files Not Serving

**Problem:** Frontend shows 404 or blank page

**Symptoms:**
- API works at `/api/health`
- But root `/` shows error

**Solutions:**
1. Check build logs - did frontend build succeed?
2. Verify `frontend/dist` folder was created
3. Check logs for: `Serving frontend from: ...`

**Debug:**
```bash
# In Render shell (if available)
ls -la frontend/dist/
```

---

### 6. WebSocket Connection Fails

**Problem:** Real-time updates don't work

**Symptoms:**
```
WebSocket connection failed
Failed to connect to wss://...
```

**Solutions:**
1. Render should support WebSockets automatically
2. Check that you're using HTTPS (not HTTP)
3. Verify `/ws/progress` endpoint is accessible

**Note:** WebSockets work on all Render plans including free tier

---

### 7. PDF Processing Fails

**Problem:** Can't process uploaded PDFs

**Symptoms:**
```
ImportError: No PDF library available
```

**Solutions:**
1. Check PyMuPDF installed: Should be in requirements.txt
2. If still fails, Render might need system libraries

**Unlikely:** PyMuPDF should work out of the box on Render

---

### 8. Large File Uploads Fail

**Problem:** Can't upload large PDFs

**Symptoms:**
```
413 Request Entity Too Large
```

**Solutions:**
Add to `backend/api.py`:
```python
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_request_size=50_000_000  # 50MB
)
```

**Note:** Render has a 100MB request limit on free tier

---

### 9. Cold Starts (Free Tier Only)

**Problem:** App takes 30+ seconds to respond after inactivity

**Symptoms:**
- First request after 15 min is slow
- Subsequent requests are fast

**This is Normal on Free Tier:**
- App spins down after 15 minutes
- Cold start takes ~30 seconds
- Upgrade to Starter plan for always-on

---

### 10. Health Check Failures

**Problem:** Render marks service as unhealthy

**Symptoms:**
```
Health check failed: /api/health returned 503
```

**Solutions:**
1. Check backend started successfully
2. Verify environment variables are set
3. Look for startup errors in logs

**Check:**
```bash
curl https://your-app.onrender.com/api/health
```

Should return: `{"status": "ok"}`

---

## 🔍 Debugging Checklist

If deployment fails, check these in order:

### 1. Build Logs
- [ ] Python dependencies installed? (look for "Successfully installed")
- [ ] Node dependencies installed? (look for "npm ci" success)
- [ ] Frontend built? (look for "vite build" output)
- [ ] No errors in build script?

### 2. Environment Variables
- [ ] `ANTHROPIC_API_KEY` OR `OPENAI_API_KEY` set?
- [ ] `LANGSMITH_API_KEY` set?
- [ ] Keys start with correct prefix?

### 3. Runtime Logs
- [ ] Server started? (look for "Starting Bridge Financial Spreader")
- [ ] Port detected? (should show port 10000)
- [ ] Frontend served? (look for "Serving frontend from")

### 4. Test Endpoints
- [ ] `/api/health` returns 200 OK?
- [ ] Root `/` serves frontend?
- [ ] `/docs` shows API documentation?
- [ ] WebSocket connects at `/ws/progress`?

---

## 🚨 Emergency Fixes

### If Build Keeps Failing

Remove pdf2image from requirements.txt (we use PyMuPDF anyway):

```bash
# Edit requirements.txt and comment out:
# pdf2image>=1.17.0
```

### If Memory Issues Persist

In `build.sh`, add before npm install:
```bash
export NODE_OPTIONS="--max-old-space-size=512"
npm ci --prefer-offline --no-audit
```

### If Nothing Works

Create a minimal test deployment:

1. Comment out all non-essential routes
2. Remove testing module imports
3. Simplify to just health check
4. Once that works, add features back one by one

---

## 📊 Expected Build Times

| Phase | Duration | What's Happening |
|-------|----------|------------------|
| Python deps | 2-3 min | Installing langchain, anthropic, etc. |
| Node deps | 1-2 min | Installing React, Vite, etc. |
| Frontend build | 30-60s | Building optimized production bundle |
| Total | 5-7 min | Should complete well under timeout |

---

## 💰 When to Upgrade from Free Tier

Upgrade to Starter ($7/month) if you experience:

- ❌ Build timeouts (> 15 minutes)
- ❌ Memory errors during build
- ❌ Cold starts are annoying users
- ❌ Need faster response times
- ✅ Want to share with team (always-on)
- ✅ Processing large PDFs regularly

---

## 🆘 Still Having Issues?

1. **Check Render Status**: https://status.render.com/
2. **Read Build Logs Carefully**: Often the error is clear
3. **Test Locally First**: Run `bash build.sh` locally
4. **Render Community**: https://community.render.com/
5. **Create Issue**: Include full build logs

---

## ✅ Success Indicators

You'll know deployment succeeded when you see:

```
✅ Build completed successfully
✅ Starting Bridge Financial Spreader API
✅ Host: 0.0.0.0
✅ Port: 10000
✅ Serving frontend from: /opt/render/project/src/frontend/dist
✅ Your service is live!
```

And visiting your URL shows the upload page! 🎉
