# GitHub Pages + GitHub Actions Serverless Deployment Guide

This guide explains how to deploy the League Tracker project using:
- **GitHub Pages** for the frontend (static files)
- **Cloudflare Workers** as the serverless backend (via GitHub Actions)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        GitHub Pages                          │
│                    (Static Frontend)                         │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  frontend/                                          │     │
│  │  ├── index.html, teams.html, matches.html          │     │
│  │  ├── app.js, api.js, config.js                     │     │
│  │  └── styles.css                                     │     │
│  └─────────────────────────────────────────────────────┘     │
│                              │                               │
│                              ▼                               │
│                    Your Browser/User                         │
│                              │                               │
│                              ▼                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │          Cloudflare Workers (Serverless)            │     │
│  │                   (workers/)                         │     │
│  │  ┌─────────────────────────────────────────────┐   │     │
│  │  │  GET /teams, /players, /matches            │   │     │
│  │  │  POST /draft/sessions, /collect            │   │     │
│  │  │  Health checks, CORS support                │   │     │
│  │  └─────────────────────────────────────────────┘   │     │
│  └─────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **GitHub Account** with repository access
2. **Cloudflare Account** (free tier is sufficient)
3. **Riot Games API Key** (for League of Legends data)

## Setup Instructions

### 1. Fork/Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/riot_api_project_ember.git
cd riot_api_project_ember
```

### 2. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and add the following secrets:

#### Required Secrets for Workers:

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token | [Create in Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens) |
| `RIOT_API_KEY` | Riot Games API key | [Get from Riot Developer Portal](https://developer.riotgames.com/) |
| `DATABASE_URL` | Database connection string | Your database URL (e.g., from Cloudflare D1 or external DB) |
| `SECRET_KEY` | Secret key for auth | Generate with `openssl rand -base64 32` |

### 3. Configure Cloudflare Workers

1. Create a Cloudflare account at https://cloudflare.com
2. Run the Wrangler login:
   ```bash
   cd workers
   npx wrangler login
   ```
3. Configure your `workers/wrangler.toml`:
   ```toml
   name = "league-tracker-api"
   compatibility_date = "2024-01-01"
   main = "src/index.js"

   [vars]
   API_VERSION = "1.0.0"
   ENVIRONMENT = "production"

   # For custom domain (optional)
   # [[routes]]
   #   pattern = "api.yourdomain.com/*"
   #   zone_name = "yourdomain.com"
   ```

### 4. Enable GitHub Pages

1. Go to your GitHub repository → Settings → Pages
2. Under "Build and deployment":
   - Source: **Deploy from a branch**
   - Branch: `gh-pages` (or `main` with `/frontend` folder)
   - Folder: `/ (root)`
3. Click Save

### 5. Configure Frontend API URL

After deploying the Workers, update `frontend/config.js` with your Workers URL:

```javascript
window.LEAGUE_TRACKER_CONFIG = {
  API_URL: 'https://your-workers-subdomain.workers.dev',
  // ... other config
};
```

Or set it as a build-time variable via GitHub Actions.

## Deployment Workflows

### Frontend Deployment (GitHub Pages)

The `deploy-pages.yml` workflow:
- Triggers on push to `main` when frontend files change
- Validates static files
- Deploys to GitHub Pages

### Backend Deployment (Cloudflare Workers)

The `deploy-workers.yml` workflow:
- Triggers on push to `main` when worker files change
- Installs dependencies
- Deploys to Cloudflare Workers

## Manual Deployment Commands

### Deploy Frontend to GitHub Pages

```bash
# Build and deploy frontend
cd frontend
npm run build

# Push to gh-pages branch
npx gh-pages -d .
```

### Deploy Workers Manually

```bash
cd workers
npm run deploy
```

## Local Development

### Run Frontend Locally

```bash
cd frontend
npm install
npm run dev
```

### Run Workers Locally

```bash
cd workers
npm install
npm run dev
```

### Connect Frontend to Local Workers

Open browser with query parameter:
```
http://localhost:3000?api=http://localhost:8787
```

## Environment Configuration

### Development (Local)

- Frontend: `http://localhost:3000` (via `npm run dev`)
- Workers: `http://localhost:8787` (via `npm run dev`)
- API URL: Use query parameter `?api=http://localhost:8787`

### Production

- Frontend: `https://YOUR_USERNAME.github.io/YOUR_REPO/`
- Workers: `https://YOUR_WORKERS_SUBDOMAIN.workers.dev`

## Troubleshooting

### CORS Errors

If you see CORS errors in the browser console:
1. Verify the Workers server is running
2. Check that the `corsHeaders` are being set in the worker response
3. Ensure the frontend is calling the correct API URL

### 404 Errors on API Calls

1. Verify the Workers URL is correct in `frontend/config.js`
2. Check that the worker routes match your API calls
3. Test the API directly: `curl https://YOUR_WORKERS_URL/health`

### Deployment Failures

- **Workers**: Check Cloudflare dashboard for error logs
- **Pages**: Check GitHub Actions tab for deployment logs

## Cost Estimation

| Service | Free Tier | Cost After Free Tier |
|---------|-----------|---------------------|
| GitHub Pages | Unlimited | Free |
| Cloudflare Workers | 100K requests/day | $5/10M requests |
| Cloudflare D1 (DB) | 5GB storage | $1/GB/month |

## Next Steps

1. Add a custom domain for both Pages and Workers
2. Set up Cloudflare D1 for database storage
3. Add authentication to the admin endpoints
4. Configure rate limiting for the API
