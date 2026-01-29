# ✅ Render Deployment Checklist

Use this checklist to deploy your app to Render.com.

## Pre-Deployment

- [x] Code committed to Git
- [x] Code pushed to GitHub
- [x] `render.yaml` configuration exists
- [ ] Have Anthropic API key ready
- [ ] Have OpenAI API key ready
- [ ] Have LangSmith API key ready

## Render Setup

- [ ] Created Render.com account
- [ ] Connected GitHub repository
- [ ] Selected "Web Service" type
- [ ] Render detected `render.yaml` config

## Environment Variables

Add these in Render dashboard:

- [ ] `ANTHROPIC_API_KEY` = `sk-ant-api03-...`
- [ ] `OPENAI_API_KEY` = `sk-...`
- [ ] `LANGSMITH_API_KEY` = `lsv2_pt_...`

## Deployment

- [ ] Clicked "Create Web Service"
- [ ] Build completed successfully
- [ ] Service shows "Live" status
- [ ] Got deployment URL

## Testing

- [ ] Opened deployment URL in browser
- [ ] Upload page loads correctly
- [ ] Tested with a sample PDF
- [ ] PDF processing works
- [ ] Results display correctly
- [ ] No console errors

## Optional

- [ ] Shared URL with team
- [ ] Set up custom domain
- [ ] Configured model in LangSmith Hub
- [ ] Upgraded to paid plan (if needed)

---

## Quick Links

- **Render Dashboard:** https://dashboard.render.com/
- **LangSmith:** https://smith.langchain.com/
- **Deployment Guide:** [DEPLOYMENT_WALKTHROUGH.md](./DEPLOYMENT_WALKTHROUGH.md)

## Your Deployment URL

```
https://[your-service-name].onrender.com
```

Write it here: _________________________________
