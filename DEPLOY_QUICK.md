# 🚀 Quick Deploy to Render.com

Deploy the Bridge Financial Spreader in 5 minutes!

## Step 1: Push to GitHub

```bash
git add .
git commit -m "Add Render deployment configuration"
git push origin master
```

## Step 2: Create Render Service

1. Go to **https://render.com** and sign in
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Render will detect `render.yaml` automatically

## Step 3: Add Environment Variables

In the Render dashboard, add these secrets:

```
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
OPENAI_API_KEY=sk-your-key-here
LANGSMITH_API_KEY=lsv2_pt_your-key-here
```

## Step 4: Deploy

Click **"Create Web Service"** and wait ~5-10 minutes.

Your app will be live at: `https://your-service-name.onrender.com`

---

## What Gets Deployed?

✅ React frontend (built and optimized)  
✅ FastAPI backend (serves API + frontend)  
✅ WebSocket support for real-time updates  
✅ Automatic HTTPS  
✅ Health monitoring  

## Free Tier

- 750 hours/month
- Spins down after 15 min inactivity
- Perfect for testing!

## Need Help?

See detailed guide: [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)
