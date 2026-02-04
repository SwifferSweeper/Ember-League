# League Tracker - Cloudflare Workers + Pages

A League of Legends league tracking application running on Cloudflare Pages and Workers for free, scalable hosting.

## Features

- **Cloudflare Workers**: Serverless backend with D1 database
- **Cloudflare Pages**: Static frontend hosting
- **D1 Database**: SQLite-compatible database for data persistence
- **KV Storage**: Session management
- **Riot API Integration**: Real-time match data collection
- **Team Management**: Create and manage teams with players
- **Match Tracking**: Automatic match collection and statistics
- **Admin Dashboard**: Secure admin interface
- **Draft Tool**: Tournament draft management

## Architecture

- **Frontend**: Static HTML/CSS/JS served from Cloudflare Pages
- **Backend**: Cloudflare Workers (Python) with D1 database
- **Database**: Cloudflare D1 (SQLite-compatible)
- **Sessions**: Cloudflare KV storage
- **Scheduled Tasks**: Cron triggers for match collection

## Prerequisites

- Cloudflare account
- Wrangler CLI installed
- Node.js and npm
- Python 3.9+

## Setup

### 1. Install Dependencies

```bash
# Install Wrangler
npm install -g wrangler

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file with your configuration:

```bash
# Cloudflare configuration
CLOUDFLARE_ACCOUNT_ID=your_account_id_here
CLOUDFARE_API_TOKEN=your_api_token_here

# Riot API configuration
RIOT_API_KEY=your_riot_api_key_here

# Application configuration
SECRET_KEY=your_secret_key_here
DEBUG=false
AUTO_COLLECT_ENABLED=true
AUTO_COLLECT_INTERVAL=5
```

### 3. Create Cloudflare Resources

Run the deployment script to create all necessary resources:

```bash
./deploy.sh
```

This will:
- Create D1 database
- Create KV namespace for sessions
- Create R2 bucket for static assets
- Set up database schema
- Deploy to Cloudflare

### 4. Manual Resource Creation (Alternative)

If you prefer manual setup:

```bash
# Create D1 database
wrangler d1 create league-tracker-db

# Create KV namespace
wrangler kv:namespace create SESSIONS

# Create R2 bucket
wrangler r2 bucket create league-tracker-assets

# Update wrangler.toml with actual resource IDs
```

### 5. Deploy

```bash
# Build and deploy
wrangler deploy

# Or use the deployment script
./deploy.sh
```

## Database Schema

The application uses Cloudflare D1 with the following tables:

- `admins`: Admin users
- `teams`: Team information
- `players`: Player information
- `team_players`: Team-player relationships
- `matches`: Match data
- `match_participants`: Player match statistics
- `draft_sessions`: Draft tournament sessions
- `draft_games`: Individual draft games
- `draft_steps`: Draft actions
- `tournament_codes`: Tournament access codes

## API Endpoints

### Teams
- `GET /api/teams` - Get all teams
- `POST /api/teams` - Create new team
- `GET /api/teams/{id}` - Get team details
- `PUT /api/teams/{id}` - Update team
- `DELETE /api/teams/{id}` - Delete team

### Players
- `GET /api/players` - Get all players

### Matches
- `GET /api/matches` - Get recent matches
- `GET /api/matches/{id}` - Get match details
- `POST /api/collect` - Trigger match collection

### Admin
- `POST /api/admin/login` - Admin login
- `POST /api/admin/logout` - Admin logout

## Scheduled Tasks

The application includes a scheduled function that runs every 5 minutes to:
- Collect match data for all players
- Update statistics
- Maintain data freshness

## Development

### Local Development

```bash
# Start local development server
wrangler dev

# Test API
curl http://localhost:8787/api/teams
```

### Testing

```bash
# Run tests
pytest
```

### Database Management

```bash
# Access database
wrangler d1 eval --binding DB "SELECT * FROM teams;"

# Run migrations
wrangler d1 eval --binding DB --file schema.sql
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `AUTO_COLLECT_ENABLED` | Enable automatic match collection | `true` |
| `AUTO_COLLECT_INTERVAL` | Match collection interval in minutes | `5` |
| `RIOT_API_KEY` | Riot API key | Required |
| `SECRET_KEY` | Flask secret key | Required |

## Deployment

### GitHub Actions

The project includes a GitHub Actions workflow for automatic deployment:

```yaml
name: Deploy to Cloudflare

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
```

### Manual Deployment

```bash
# Build and deploy
wrangler deploy

# Or with environment variables
wrangler deploy --env production
```

## Cost Optimization

This setup is designed to be cost-effective:

- **Cloudflare Workers**: Free tier includes 100,000 requests/day
- **Cloudflare Pages**: Free tier includes unlimited requests
- **Cloudflare D1**: Free tier includes 100,000 queries/day
- **Cloudflare KV**: Free tier includes 100,000 reads/day

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure D1 database is created and IDs are updated in wrangler.toml
   - Check resource bindings in Cloudflare dashboard

2. **Riot API Errors**
   - Verify RIOT_API_KEY is set and valid
   - Check rate limits (100 requests/minute for development)

3. **Deployment Issues**
   - Ensure all required environment variables are set
   - Check wrangler.toml configuration
   - Verify Cloudflare account permissions

4. **Scheduled Tasks Not Running**
   - Check cron trigger configuration
   - Verify scheduled function is exported
   - Check Cloudflare dashboard for execution logs

### Debug Mode

Enable debug mode to get more detailed error messages:

```bash
# Set environment variable
DEBUG=true

# Or in wrangler.toml
[vars]
DEBUG = "true"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Check the Cloudflare Workers documentation
- Review the Riot API documentation
