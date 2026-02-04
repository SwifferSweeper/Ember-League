# Deployment Guide

This document describes how to deploy the League Tracker application using GitHub Pages for the frontend and Cloudflare Workers for the serverless backend.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Pages                           │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  frontend/                                          │
│   │  ├── index.html                                    │
│   │  ├── teams.html                                    │
│   │  ├── matches.html                                  │
│   │  ├── leaderboards.html                             │
│   │  ├── draft.html                                    │
│   │  ├── styles.css                                    │
│   │  ├── api.js                                        │
│   │  └── app.js                                        │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ API Calls
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Cloudflare Workers                         │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  workers/                                           │
│   │  ├── src/index.js  (API handlers)                   │
│   │  └── wrangler.toml (Configuration)                  │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **GitHub Account** with a repository
2. **Cloudflare Account** (free tier is sufficient)
3. **Riot Games API Key** (for League of Legends data)

## Step 1: Deploy Frontend to GitHub Pages

### Automatic Deployment (Recommended)

1. Push the `frontend/` directory to your GitHub repository
2. Go to your repository settings → Pages
3. Under "Build and deployment":
   - Source: Select "GitHub Actions"
4. The workflow `.github/workflows/deploy-pages.yml` will automatically deploy on push to main

## Step 2: Deploy Backend to Cloudflare Workers

### Install Wrangler CLI

```bash
npm install -g wrangler
```

### Login to Cloudflare

```bash
wrangler login
```

### Configure Secrets

```bash
cd workers
wrangler secret put RIOT_API_KEY
wrangler secret put DATABASE_URL
wrangler secret put SECRET_KEY
```

### Deploy to Production

```bash
cd workers
wrangler deploy
```

## Step 3: Configure API URL

Edit `frontend/api.js`:

```javascript
const API_BASE_URL = 'https://your-worker.yourname.workers.dev/api';
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/teams` | GET | List all teams |
| `/api/teams/:id` | GET | Get team details |
| `/api/teams/register` | POST | Register a new team |
| `/api/players/:puuid/matches` | GET | Get player matches |
| `/api/players/:puuid/stats` | GET | Get player stats |
| `/api/league/matches` | GET | Get league matches |
| `/api/draft/sessions` | GET | List draft sessions |
| `/api/champions` | GET | List champions |

## Development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend (Workers)

```bash
cd workers
npm install
npm run dev
```

## Cost Estimation

- **GitHub Pages**: Free
- **Cloudflare Workers**: Free tier includes 100,000 requests/day
