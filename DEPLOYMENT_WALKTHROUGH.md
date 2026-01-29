# 🎉 Render Deployment - Step by Step Guide

Your code is ready! Follow these steps to deploy to Render.com.

## ✅ Prerequisites Complete

- [x] Code pushed to GitHub
- [x] `render.yaml` configuration created
- [x] Backend updated to serve frontend
- [x] Environment variables documented

## 🚀 Deployment Steps

### Step 1: Create Render Account (2 minutes)

1. Go to **https://render.com/**
2. Click **"Get Started"**
3. Sign up with GitHub (easiest) or email
4. Verify your email if needed

### Step 2: Connect GitHub Repository (1 minute)

1. In Render dashboard, click **"New +"** in top right
2. Select **"Web Service"**
3. Click **"Connect account"** under GitHub
4. Authorize Render to access your GitHub
5. Find your repository: `bridge-financial-spreading`
6. Click **"Connect"**

### Step 3: Configure Service (2 minutes)

Render will auto-detect your `render.yaml` file and show:

```yaml
✓ Name: bridge-financial-spreader
✓ Environment: Python
✓ Region: Oregon
✓ Build Command: pip install... && npm install && npm run build
✓ Start Command: python backend/main.py
```

**You don't need to change anything!** Just click **"Next"** or **"Continue"**

### Step 4: Add Environment Variables (2 minutes)

This is the **MOST IMPORTANT** step. Add these in the Render dashboard:

1. Scroll to **"Environment Variables"** section
2. Click **"Add Environment Variable"**

Add these THREE required variables:

```
Key: ANTHROPIC_API_KEY
Value: sk-ant-api03-YOUR-ACTUAL-KEY-HERE
```

```
Key: OPENAI_API_KEY  
Value: sk-YOUR-ACTUAL-KEY-HERE
```

```
Key: LANGSMITH_API_KEY
Value: lsv2_pt_YOUR-ACTUAL-KEY-HERE
```

**Where to find your keys:**
- Anthropic: https://console.anthropic.com/settings/keys
- OpenAI: https://platform.openai.com/api-keys
- LangSmith: https://smith.langchain.com/settings

### Step 5: Deploy! (5-10 minutes)

1. Click **"Create Web Service"** at the bottom
2. Render will start building your app
3. Watch the logs in real-time

**Build process:**
```
[1/4] Installing Python dependencies... ✓
[2/4] Installing Node dependencies... ✓
[3/4] Building React frontend... ✓
[4/4] Starting server... ✓
```

When you see:
```
Bridge Financial Spreader - API Server
Host: 0.0.0.0
Port: 10000
==> Your service is live! 🎉
```

### Step 6: Test Your Deployment (2 minutes)

1. Render will show you a URL like:
   ```
   https://bridge-financial-spreader-abcd.onrender.com
   ```

2. Click the URL to open your app
3. You should see the upload page
4. Try uploading a financial statement PDF
5. Check that it processes correctly

### Step 7: Share with Others

Your app is now live! Share the URL with your team:

```
https://your-service-name.onrender.com
```

## 🎛️ Free Tier Details

Your app runs on Render's **free tier** which includes:

- ✅ 750 hours/month (enough for one always-on service)
- ⚠️ Spins down after 15 minutes of inactivity
- ⏱️ Cold starts take ~30 seconds when waking up
- ✅ Automatic HTTPS
- ✅ Custom domain support

**For production use:** Upgrade to Starter plan ($7/month) for always-on service.

## 🔍 Monitoring Your App

### View Logs

1. Go to your service in Render dashboard
2. Click **"Logs"** tab
3. See real-time application logs

### Check Metrics

Click **"Metrics"** tab to see:
- CPU usage
- Memory usage
- Request count
- Response times

### LangSmith Tracing

View detailed AI model traces at:
https://smith.langchain.com/

## 🐛 Troubleshooting

### Problem: Build fails with "command not found"

**Solution:** Check that both `requirements.txt` files exist in the repo

### Problem: "No AI API keys set" error

**Solution:** 
1. Go to your service → Settings
2. Scroll to Environment Variables
3. Verify `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is set
4. Click "Manual Deploy" → "Deploy latest commit"

### Problem: Page shows 404 Not Found

**Solution:** 
1. Check logs for startup errors
2. Make sure frontend built successfully (look for "dist" folder in logs)
3. Check that `/api/health` returns 200 OK

### Problem: WebSocket connection fails

**Solution:** 
1. WebSocket should work automatically over WSS in production
2. Check browser console for errors
3. Make sure you're using HTTPS (not HTTP)

### Problem: Cold starts are too slow

**Solution:** Upgrade to Starter plan ($7/month) for always-on service

## 📈 Next Steps

### 1. Custom Domain (Optional)

1. Go to Settings → Custom Domain
2. Add your domain (e.g., `spreader.yourcompany.com`)
3. Update DNS records as instructed
4. Render provides free SSL automatically

### 2. Configure Model in LangSmith

1. Go to https://smith.langchain.com/hub
2. Find your prompt: `financial-spreader/income-statement`
3. Click Edit → Change model
4. Changes take effect immediately (no redeploy needed!)

### 3. Upgrade Plan (If Needed)

Free tier → Starter ($7/mo) → Standard ($25/mo)

Upgrade when:
- You want always-on service (no cold starts)
- You need more memory
- You have high traffic

## 🎓 Resources

- **Render Docs:** https://render.com/docs
- **Render Community:** https://community.render.com/
- **Your deployment guide:** RENDER_DEPLOYMENT.md (detailed version)
- **Quick reference:** DEPLOY_QUICK.md

## ✨ You're Done!

Your Bridge Financial Spreader is now:
- ✅ Deployed to production
- ✅ Accessible via HTTPS
- ✅ Backed by professional infrastructure
- ✅ Ready to share with your team

**Your deployment URL:**
```
https://your-service-name.onrender.com
```

🎉 Congratulations! 🎉
