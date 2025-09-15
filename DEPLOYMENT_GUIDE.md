# JOE Market Tracker - Deployment Guide

## 🚀 Deployment Options

### Option 1: GitHub Pages (FREE - Recommended) 
**Best for:** Static site with automated updates via GitHub Actions

#### Setup:
1. **Create GitHub Repository**
   ```bash
   # Generate static site
   python generate_static_site.py
   
   # Initialize git
   git init
   git add .
   git commit -m "Initial commit"
   
   # Create repo on GitHub and push
   git remote add origin https://github.com/YOUR_USERNAME/joe-tracker.git
   git push -u origin main
   ```

2. **Enable GitHub Pages**
   - Go to Settings → Pages
   - Source: Deploy from branch
   - Branch: main, folder: /docs
   - Save

3. **Enable GitHub Actions**
   - Go to Settings → Actions → General
   - Enable "Allow all actions"

4. **Your site will be live at:**
   ```
   https://YOUR_USERNAME.github.io/joe-tracker/
   ```

**Pros:**
- ✅ Completely free
- ✅ Automatic weekly updates (Fridays at 5pm EST) via GitHub Actions
- ✅ No server needed
- ✅ Custom domain support

**Cons:**
- ❌ Selenium scraping runs on GitHub Actions (usage limits apply)
- ❌ Static site only (no real-time features)

---

### Option 2: Streamlit Cloud (FREE)
**Best for:** Interactive app with Python backend

#### Setup:
1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git push
   ```

2. **Deploy on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect GitHub account
   - Select repository
   - Main file: `joe_app.py`
   - Click Deploy

3. **Add secrets for automation**
   - In Streamlit Cloud settings, add secrets:
   ```toml
   [general]
   auto_update = true
   update_hour = 17  # 5pm
   ```

**Pros:**
- ✅ Free tier available
- ✅ Full Python/Streamlit features
- ✅ Interactive visualizations

**Cons:**
- ❌ Limited to 1 public app on free tier
- ❌ Selenium might not work (no Chrome browser)
- ❌ Need workaround for daily updates

---

### Option 3: Render (FREE tier available)
**Best for:** Full-featured app with background jobs

#### Setup:
1. **Create `render.yaml`**
   ```yaml
   services:
     - type: web
       name: joe-tracker
       env: python
       buildCommand: "pip install -r requirements.txt"
       startCommand: "streamlit run joe_app.py --server.port $PORT"
       envVars:
         - key: PORT
           value: 8501
   
     - type: cron
       name: joe-updater
       env: python
       schedule: "0 22 * * 5"  # 5pm EST every Friday
       buildCommand: "pip install -r requirements.txt"
       startCommand: "python joe_working_scraper.py --years 1"
   ```

2. **Deploy**
   - Push to GitHub
   - Connect Render to GitHub
   - Create new Blueprint
   - Select repository

**Pros:**
- ✅ Free tier (750 hours/month)
- ✅ Supports cron jobs
- ✅ Can run Selenium

**Cons:**
- ❌ App sleeps after 15 min inactivity on free tier
- ❌ Limited compute resources

---

### Option 4: Railway (Simple deployment)
**Best for:** Quick deployment with minimal configuration

#### Setup:
1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. **Deploy**
   ```bash
   railway init
   railway up
   ```

3. **Add cron job**
   ```bash
   railway run python joe_working_scraper.py --years 1
   ```

**Pros:**
- ✅ $5 free credit monthly
- ✅ Simple deployment
- ✅ Supports background jobs

**Cons:**
- ❌ Limited free tier
- ❌ Charges after free credit

---

### Option 5: Google Cloud Run (FREE tier)
**Best for:** Scalable containerized app

#### Setup:
1. **Create `Dockerfile`**
   ```dockerfile
   FROM python:3.9-slim
   
   # Install Chrome
   RUN apt-get update && apt-get install -y \
       wget gnupg unzip curl \
       && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
       && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
       && apt-get update \
       && apt-get install -y google-chrome-stable \
       && rm -rf /var/lib/apt/lists/*
   
   WORKDIR /app
   COPY . .
   RUN pip install -r requirements.txt
   
   CMD streamlit run joe_app.py --server.port $PORT
   ```

2. **Deploy**
   ```bash
   gcloud run deploy joe-tracker \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

3. **Add Cloud Scheduler for updates**
   ```bash
   gcloud scheduler jobs create http joe-update \
     --schedule="0 17 * * *" \
     --uri="https://joe-tracker-xxx.run.app/update" \
     --http-method=POST
   ```

**Pros:**
- ✅ Generous free tier
- ✅ Auto-scaling
- ✅ Professional infrastructure

**Cons:**
- ❌ More complex setup
- ❌ Requires Google Cloud account

---

## 🏆 Recommended Approach

For your use case (free, easy, with Selenium scraping):

### **Best Solution: Hybrid Approach**

1. **GitHub Pages for the frontend** (free, reliable)
2. **GitHub Actions for daily scraping** (free, 2000 min/month)
3. **Data stored in repository** (automatically updated)

#### Implementation:
```bash
# 1. Generate static site
python generate_static_site.py

# 2. Create GitHub repo and push
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/joe-tracker.git
git push -u origin main

# 3. Enable GitHub Pages (Settings → Pages → /docs folder)

# 4. Site is live! Updates automatically at 5pm every Friday
```

The GitHub Action (already created by `generate_static_site.py`) will:
- Run every Friday at 5pm EST
- Scrape latest JOE data using Selenium
- Update the JSON data file
- Commit changes
- Site automatically updates

**Your site URL:**
```
https://YOUR_USERNAME.github.io/joe-tracker/
```

---

## 📝 Environment Variables

For any deployment, set these environment variables:

```env
# Scraper settings
HEADLESS_BROWSER=true
UPDATE_HOUR=17  # 5pm
UPDATE_MINUTE=0

# Optional: Email notifications
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_FROM=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_TO=notify@example.com
```

---

## 🔧 Troubleshooting

### Selenium Issues
- **Chrome not found**: Use Docker image with Chrome pre-installed
- **Timeout errors**: Increase timeout in scraper settings
- **Memory issues**: Use headless mode, reduce parallel downloads

### GitHub Actions
- **Workflow not running**: Check Actions are enabled in Settings
- **Chrome installation fails**: Use `browser-actions/setup-chrome@latest`
- **Commit fails**: Ensure workflow has write permissions

### Data Issues
- **Duplicate data**: Check file naming in scraped/ folder
- **Missing years**: Verify scraper date ranges
- **Wrong sections**: Check filter logic in scraper

---

## 📊 Monitoring

Add monitoring to track your deployment:

1. **GitHub Actions**: Check workflow runs in Actions tab
2. **Uptime monitoring**: Use UptimeRobot (free) to monitor site
3. **Error notifications**: Configure email alerts in scraper
4. **Data validation**: Add checks for data consistency

---

## 🎯 Quick Start Commands

```bash
# Local testing
python joe_app.py  # Streamlit version
python -m http.server 8000 --directory docs  # Static version

# Generate static site
python generate_static_site.py

# Run scraper
python joe_working_scraper.py --test

# Deploy to GitHub Pages
git add . && git commit -m "Update" && git push
```

Your JOE tracker will be live and auto-updating daily! 🚀