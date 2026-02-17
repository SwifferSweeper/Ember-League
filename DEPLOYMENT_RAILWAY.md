# Railway Deployment Guide

This guide explains how to deploy the League Tracker project using Railway as the hosting platform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Railway                               │
│                   (Full-Stack Hosting)                      │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Flask Application (Python)                         │     │
│  │  ├── Static files (frontend)                        │     │
│  │  ├── Templates (HTML)                              │     │
│  │  └── API routes                                     │     │
│  │                                                    │     │
│  │  PostgreSQL Database (or SQLite)                    │     │
│  │                                                    │     │
│  │  Background Scheduler (APScheduler)                 │     │
│  └─────────────────────────────────────────────────────┘     │
│                              │                               │
│                              ▼                               │
│                    Your Browser/User                         │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Railway Account** - Sign up at https://railway.app
2. **GitHub Account** with repository access
3. **Riot Games API Key** (for League of Legends data)

## Quick Deployment Steps

### 1. Fork/Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/riot_api_project_ember.git
cd riot_api_project_ember
```

### 2. Create a Railway Project

**Important:** Create your service in the **project root** (where `Procfile` is), NOT in the `league_tracker` subfolder.

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. **Do NOT select `league_tracker` as root** - Railway will deploy from where `Procfile` is located (project root)

### 3. Configure Root Directory (If Needed)

If Railway doesn't auto-detect the correct directory, you have two options:

#### Option A: Set Root Directory

1. Go to your service in Railway dashboard
2. Click "Settings"
3. Find "Root Directory" or "Build Path"
4. Set it to **empty** (this is the recommended approach)
5. Click "Save"
6. Redeploy

#### Option B: Use Custom Build Command

1. Go to your service in Railway dashboard
2. Click "Settings"
3. Find "Custom Build Command"
4. Enter:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
5. Click "Save"
6. Redeploy

### 3. Configure Environment Variables

In the Railway dashboard, go to your service's "Variables" tab and add:

| Variable | Description | How to Get |
|----------|-------------|------------|
| `DATABASE_URL` | PostgreSQL connection string | Auto-provided by Railway |
| `RIOT_API_KEY` | Riot Games API key | [Get from Riot Developer Portal](https://developer.riotgames.com/) |
| `SECRET_KEY` | Secret key for auth | Generate with `openssl rand -base64 32` |
| `DEBUG` | Set to `False` for production | Optional |
| `AUTO_COLLECT_ENABLED` | Enable auto match collection | Optional (`True`/`False`) |
| `AUTO_COLLECT_INTERVAL` | Collection interval in minutes | Optional (default: 5) |

### 4. Set Up Database

1. In Railway dashboard, click "Add Database"
2. Select "PostgreSQL"
3. Railway will automatically set `DATABASE_URL`

### 5. Deploy

Railway will:
1. Detect Python from `requirements.txt`
2. Use `Procfile` for the start command
3. Start the web server on port $PORT
4. If deployment fails, check the logs in Railway dashboard

**Important:** After pushing changes:
1. Go to Railway dashboard
2. Click "Deploy" (or "Redeploy") to pull the latest changes
3. If still failing, try clearing the Railway cache:
   - Go to Settings → General
   - Click "Clear Build Cache"
   - Redeploy again

**Important:** In Railway dashboard settings, ensure:
- Root Directory is **empty** (this is the recommended approach)
- If you selected the wrong directory initially, redeploy with correct settings

The deployment uses:
```
web: gunicorn --bind 0.0.0.0:$PORT league_tracker.app:app --workers 4 --threads 4 --timeout 120
```

### 6. Access Your App

After deployment, Railway provides a URL like:
```
https://league-tracker-production.up.railway.app
```

## Manual Deployment with Railway CLI

### Install Railway CLI

```bash
npm install -g @railway/cli
```

### Login to Railway

```bash
railway login
```

### Initialize Project

```bash
railway init
```

### Set Environment Variables

```bash
railway variables set RIOT_API_KEY=your_api_key
railway variables set SECRET_KEY=your_secret_key
```

### Deploy

```bash
railway up
```

### Open in Browser

```bash
railway open
```

## Database Setup

### PostgreSQL (Recommended for Production)

Railway provides PostgreSQL automatically:
1. Add a PostgreSQL database in Railway dashboard
2. `DATABASE_URL` is auto-set
3. Flask will connect automatically

### SQLite (For Development)

If you prefer SQLite for local development:
1. Don't set `DATABASE_URL` in your `.env` file
2. The app will use SQLite locally

## Local Development with Railway

### Link to Remote Database

```bash
railway link
railway run python manage.py migrate
railway run python manage.py runserver
```

### Use Local Database

```bash
# Set DATABASE_URL to empty in .env
DATABASE_URL=
```

## Environment Configuration

### Development (Local)

```bash
# .env file
DATABASE_URL=
RIOT_API_KEY=your_api_key
SECRET_KEY=dev-secret-key
DEBUG=True
AUTO_COLLECT_ENABLED=False
```

### Production (Railway)

Environment variables are set in Railway dashboard:

```
DATABASE_URL=postgres://user:pass@host:5432/db
RIOT_API_KEY=your_production_api_key
SECRET_KEY=secure-random-key
DEBUG=False
AUTO_COLLECT_ENABLED=True
AUTO_COLLECT_INTERVAL=5
```

## Troubleshooting

### Application Won't Start

1. Check logs in Railway dashboard
2. Verify all environment variables are set
3. Ensure `requirements.txt` has all dependencies

### Database Connection Issues

1. Verify `DATABASE_URL` is set correctly
2. Check if database service is running
3. Try restarting the service

### "No module named 'app'" Error

This usually means Railway is using a cached deployment:

1. Go to Railway dashboard → Your service → Settings
2. Find "Clear Build Cache" or "Clear Cache"
3. Click to clear the cache
4. Redeploy your service

Also ensure:
- Root Directory is **empty**
- You've pushed all changes to GitHub
- Railway is deploying the correct branch

### "No module named 'league_tracker'" Error

This means the PYTHONPATH is not set correctly:

1. Ensure `railway.json` is in the project root
2. Verify the project structure:
   ```
   /project-root/
   ├── railway.json
   ├── Procfile
   ├── requirements.txt
   └── league_tracker/
       ├── app.py
       └── ...
   ```
3. Redeploy after ensuring correct structure

### CORS Errors

1. Railway doesn't require CORS configuration for same-origin
2. If using a custom domain, ensure it's configured in Railway

### 404 Errors on Routes

1. Verify the Flask app is running
2. Check that all routes are correctly defined
3. Review Railway logs for specific errors

### Static Files Not Loading

1. Ensure static files are in `league_tracker/static/`
2. Flask serves static files automatically
3. Check browser devtools for failed requests

## Cost Estimation

| Service | Free Tier | Cost After Free Tier |
|---------|-----------|---------------------|
| Railway | $5 credit/month | $0.10/service/hour |
| PostgreSQL | Included | $0.01/GB/month storage |

## Migrating from GitHub Pages + Cloudflare Workers

If you're migrating from the previous setup:

1. **Remove GitHub Pages deployment files**:
   - Delete `frontend/` directory (if separate)
   - Remove `workers/` directory

2. **Update API URLs**:
   - Old: `https://your-workers.workers.dev`
   - New: `https://your-app.up.railway.app`

3. **Update frontend config** if you have a separate frontend:
   ```javascript
   window.LEAGUE_TRACKER_CONFIG = {
     API_URL: 'https://your-app.up.railway.app',
   };
   ```

4. **Remove old GitHub Actions workflows**:
   - Delete `.github/workflows/deploy-pages.yml`
   - Delete `.github/workflows/deploy-workers.yml`

## Health Check

Railway uses `/` as the health check endpoint. The Flask app returns the home page at this route.

## Scaling

To scale your application:

1. Go to Railway dashboard
2. Select your service
3. Adjust the replica count under "Settings"
4. Railway will automatically distribute traffic

## Next Steps

1. Add a custom domain in Railway settings
2. Set up monitoring and alerts
3. Configure backup for PostgreSQL database
4. Set up staging environment
