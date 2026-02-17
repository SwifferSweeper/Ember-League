# Deployment Guide

This document describes how to deploy the League Tracker application.

## Railway (Recommended)

The easiest way to deploy the full-stack application including database.

**See [DEPLOYMENT_RAILWAY.md](./DEPLOYMENT_RAILWAY.md) for detailed instructions.**

## Quick Start: Railway Deployment

1. Create a Railway account at https://railway.app
2. Connect your GitHub repository
3. Add a PostgreSQL database
4. Set environment variables:
   - `RIOT_API_KEY` - Your Riot Games API key
   - `SECRET_KEY` - Generate with `openssl rand -base64 32`
5. Deploy!

## Quick Start: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Set variables
railway variables set RIOT_API_KEY=your_api_key

# Deploy
railway up
```

## Architecture

The application is a Flask web app that includes:
- **Frontend**: HTML templates with Jinja2
- **Backend**: Flask REST API
- **Database**: PostgreSQL (Railway)
- **Scheduler**: Background task scheduler for match collection

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | No | PostgreSQL connection string (auto-set on Railway) |
| `RIOT_API_KEY` | Yes | Riot Games API key |
| `SECRET_KEY` | Yes | Secret key for sessions |
| `DEBUG` | No | Set to `False` for production |
| `AUTO_COLLECT_ENABLED` | No | Enable automatic match collection |
| `AUTO_COLLECT_INTERVAL` | No | Collection interval in minutes |

## Cost Estimation

| Platform | Free Tier | Notes |
|----------|-----------|-------|
| Railway | $5 credit/month | $0.10/service/hour |
| PostgreSQL | Included | Storage costs extra |
