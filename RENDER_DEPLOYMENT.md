# Deployment Guide - Render.com

This guide will help you deploy the Bridge Financial Spreader to Render.com.

## Prerequisites

1. GitHub account with your code pushed to a repository
2. Render.com account (free tier available)
3. API keys ready:
   - Anthropic API key (for Claude models)
   - OpenAI API key (for GPT models) 
   - LangSmith API key (for tracing and observability)

## Quick Start (5 minutes)

### Step 1: Push Code to GitHub

```bash
# Make sure all changes are committed
git add .
git commit -m "Add Render deployment configuration"
git push origin master
```

### Step 2: Create New Service on Render

1. Go to https://render.com/
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Render will auto-detect the `render.yaml` configuration

### Step 3: Configure Environment Variables

In the Render dashboard, add these environment variables:

**Required:**
- `ANTHROPIC_API_KEY` = `sk-ant-api03-...` (your Anthropic API key)
- `OPENAI_API_KEY` = `sk-...` (your OpenAI API key)
- `LANGSMITH_API_KEY` = `lsv2_pt_...` (your LangSmith API key)

**Optional (already set in render.yaml):**
- `LANGSMITH_PROJECT` = `financial-spreader-production`
- `API_HOST` = `0.0.0.0`
- `API_PORT` = `10000`

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Install Python dependencies
   - Install Node.js dependencies
   - Build the React frontend
   - Start the FastAPI backend
   - Serve both frontend and API from one service

3. Wait 5-10 minutes for the first deployment

### Step 5: Test Your Deployment

Once deployed, you'll get a URL like: `https://bridge-financial-spreader.onrender.com`

Test it:
1. Open the URL in your browser
2. You should see the upload page
3. Try uploading a financial statement PDF
4. Check that the spreading works

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Render Web Service                                      │
│ https://your-app.onrender.com                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  FastAPI Backend (Python)                              │
│  ├─ Serves API at /api/*                               │
│  ├─ WebSocket at /ws/*                                 │
│  └─ Serves React frontend from /frontend/dist         │
│                                                         │
│  React Frontend (Static Files)                         │
│  └─ Built with: npm run build                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Build Process

Render runs this build command (defined in `render.yaml`):

```bash
# 1. Install Python dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt

# 2. Install Node.js dependencies and build frontend
cd frontend && npm install && npm run build && cd ..
```

This creates `frontend/dist/` with optimized production files.

## Start Command

```bash
python backend/main.py
```

The FastAPI server:
1. Starts on port 10000 (Render's default)
2. Serves API routes at `/api/*`
3. Serves WebSocket at `/ws/*`
4. Serves frontend static files from `frontend/dist/`

## Pricing

**Free Tier:**
- 750 hours/month (enough for one always-on service)
- Service spins down after 15 minutes of inactivity
- Cold starts take ~30 seconds
- Perfect for testing

**Starter Plan ($7/month):**
- Always-on service (no cold starts)
- 1 GB RAM
- Recommended for sharing with others

## Troubleshooting

### Build Fails

**Problem:** `npm install` fails
**Solution:** Check that `frontend/package.json` exists and is valid

**Problem:** Python package installation fails
**Solution:** Check that both `requirements.txt` files are valid

### Runtime Errors

**Problem:** "No AI API keys set"
**Solution:** Add `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in Render dashboard

**Problem:** 404 on frontend routes
**Solution:** The catch-all route in `backend/api.py` should handle this. Check logs.

**Problem:** WebSocket connection fails
**Solution:** Make sure the frontend connects to the same domain (no localhost references)

### Check Logs

View logs in Render dashboard:
1. Go to your service
2. Click **"Logs"** tab
3. Look for startup messages and errors

## Custom Domain

To add a custom domain:

1. Go to your service in Render
2. Click **"Settings"**
3. Scroll to **"Custom Domain"**
4. Add your domain (e.g., `spreader.yourdomain.com`)
5. Update DNS records as instructed

Render provides free SSL certificates automatically.

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key for Claude models | `sk-ant-api03-...` |
| `OPENAI_API_KEY` | Yes* | OpenAI API key for GPT models | `sk-...` |
| `LANGSMITH_API_KEY` | Yes | LangSmith API key for tracing | `lsv2_pt_...` |
| `LANGSMITH_PROJECT` | No | Project name in LangSmith | `financial-spreader-production` |
| `API_HOST` | No | Host to bind to | `0.0.0.0` |
| `API_PORT` | No | Port to listen on | `10000` |
| `ANTHROPIC_MODEL` | No | Default Claude model | `claude-sonnet-4-5` |
| `OPENAI_MODEL` | No | Default GPT model | `gpt-5.2` |

*At least one AI provider API key is required

## Updating Your Deployment

To deploy updates:

```bash
# 1. Make changes locally
# 2. Commit and push
git add .
git commit -m "Your update message"
git push origin master

# 3. Render auto-deploys from master branch
```

Render will automatically:
- Detect the push
- Rebuild the application
- Deploy the new version
- Zero-downtime deployment

## Monitoring

**Health Check:**
Render automatically monitors `/api/health` endpoint every 30 seconds.

**Metrics:**
View in Render dashboard:
- CPU usage
- Memory usage
- Request count
- Response times

**LangSmith Tracing:**
View detailed AI model traces at https://smith.langchain.com/

## Scaling

If you need more resources:

1. Go to **Settings** → **Instance Type**
2. Upgrade to higher tier:
   - Standard: 2 GB RAM
   - Pro: 4 GB RAM
   - Pro Plus: 8+ GB RAM

## Security Best Practices

1. ✅ Never commit `.env` file (already in `.gitignore`)
2. ✅ Use Render's environment variables for secrets
3. ✅ Enable HTTPS (automatic with Render)
4. ✅ Regularly rotate API keys
5. ✅ Monitor LangSmith for unexpected usage

## Support

- **Render Docs:** https://render.com/docs
- **Render Community:** https://community.render.com/
- **This App:** Check logs in Render dashboard

## Next Steps

After deployment:

1. ✅ Test with example financial statements
2. ✅ Share the URL with your team
3. ✅ Monitor usage in LangSmith
4. ✅ Set up custom domain (optional)
5. ✅ Configure model preferences in LangSmith Hub
