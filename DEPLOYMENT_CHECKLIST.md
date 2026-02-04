# Deployment Checklist

## Prerequisites
- [ ] Cloudflare account with Workers and Pages enabled
- [ ] Wrangler CLI installed (`npm install -g wrangler`)
- [ ] Node.js and npm installed
- [ ] Python 3.9+ installed
- [ ] Riot API key obtained from Riot Developer Portal

## Environment Configuration
- [ ] Create `.env` file with required variables
- [ ] Set `CLOUDFLARE_ACCOUNT_ID`
- [ ] Set `CLOUDFARE_API_TOKEN` (with Workers and Pages permissions)
- [ ] Set `RIOT_API_KEY` (from Riot Developer Portal)
- [ ] Set `SECRET_KEY` (random string for Flask sessions)
- [ ] Set `DEBUG=false` for production
- [ ] Set `AUTO_COLLECT_ENABLED=true`
- [ ] Set `AUTO_COLLECT_INTERVAL=5`

## Cloudflare Resources
- [ ] D1 database created (`wrangler d1 create league-tracker-db`)
- [ ] KV namespace created (`wrangler kv:namespace create SESSIONS`)
- [ ] R2 bucket created (`wrangler r2 bucket create league-tracker-assets`)
- [ ] Resource IDs updated in `wrangler.toml`
- [ ] Secrets set in Cloudflare dashboard

## Database Setup
- [ ] Database schema created (`wrangler d1 eval --file schema.sql`)
- [ ] Default admin user created
- [ ] Tables verified in D1 database

## Deployment
- [ ] Dependencies installed (`npm install`)
- [ ] Project built (`npm run build`)
- [ ] Deployed to Cloudflare (`wrangler deploy`)
- [ ] Frontend deployed to Cloudflare Pages
- [ ] Custom domain configured (if needed)

## Testing
- [ ] API endpoints tested
- [ ] Frontend loads correctly
- [ ] Database connections working
- [ ] Scheduled tasks running
- [ ] Authentication working
- [ ] Error handling verified

## Security
- [ ] Environment variables secured
- [ ] API keys not exposed in code
- [ ] HTTPS enforced
- [ ] Input validation implemented
- [ ] SQL injection prevention
- [ ] XSS protection

## Monitoring
- [ ] Cloudflare dashboard monitored
- [ ] Error logs checked
- [ ] Performance metrics reviewed
- [ ] Scheduled task logs verified
- [ ] Database query performance checked

## Post-Deployment
- [ ] Admin login tested
- [ ] Team creation tested
- [ ] Match collection tested
- [ ] Draft tool tested
- [ ] All features verified
- [ ] Documentation updated

## Backup & Recovery
- [ ] Database backup strategy defined
- [ ] Environment variables documented
- [ ] Deployment rollback plan ready
- [ ] Monitoring alerts configured

## Performance
- [ ] Page load times checked
- [ ] API response times verified
- [ ] Database query optimization
- [ ] Caching strategy implemented
- [ ] CDN configuration verified

## Cost Management
- [ ] Usage limits monitored
- [ ] Free tier limits respected
- [ ] Cost alerts configured
- [ ] Resource cleanup scheduled
- [ ] Optimization opportunities identified

## Final Verification
- [ ] All tests passing
- [ ] Application accessible
- [ ] Features working
- [ ] Security measures in place
- [ ] Documentation complete
- [ ] Team notified of deployment