// League Tracker - Cloudflare Workers Serverless Backend
import { Router, error, json } from 'itty-router';

// Create router
const router = Router();

// Environment variables
const API_VERSION = API_VERSION || '1.0.0';
const ENVIRONMENT = ENVIRONMENT || 'development';

// CORS headers
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

// Handle CORS preflight
router.options('*', () => {
  return new Response(null, {
    status: 204,
    headers: corsHeaders,
  });
});

// Health check endpoint
router.get('/health', () => {
  return json({
    status: 'healthy',
    version: API_VERSION,
    environment: ENVIRONMENT,
    timestamp: new Date().toISOString(),
  }, { headers: corsHeaders });
});

// API info endpoint
router.get('/api', () => {
  return json({
    name: 'League Tracker API',
    version: API_VERSION,
    endpoints: {
      health: '/health',
      teams: '/teams',
      players: '/players',
      matches: '/matches',
      drafts: '/draft/sessions',
      champions: '/champions',
    },
  }, { headers: corsHeaders });
});

// ==================== Teams ====================

router.get('/teams', async () => {
  // TODO: Implement team fetching from database
  return json({
    teams: [],
    message: 'Teams endpoint - database connection required',
  }, { headers: corsHeaders });
});

router.get('/teams/:teamId', async ({ params }) => {
  const { teamId } = params;
  return json({
    teamId,
    message: `Team ${teamId} details`,
  }, { headers: corsHeaders });
});

router.post('/teams/register', async (request) => {
  const data = await request.json();
  return json({
    success: true,
    message: 'Team registered',
    data,
  }, { headers: corsHeaders, status: 201 });
});

// ==================== Players ====================

router.get('/players/:puuid', async ({ params }) => {
  const { puuid } = params;
  return json({
    puuid,
    message: `Player ${puuid} details`,
  }, { headers: corsHeaders });
});

router.get('/players/:puuid/matches', async ({ params }) => {
  const { puuid } = params;
  return json({
    puuid,
    matches: [],
    message: `Matches for player ${puuid}`,
  }, { headers: corsHeaders });
});

router.get('/players/:puuid/stats', async ({ params }) => {
  const { puuid } = params;
  return json({
    puuid,
    stats: {},
    message: `Stats for player ${puuid}`,
  }, { headers: corsHeaders });
});

// ==================== Matches ====================

router.get('/matches', async ({ query }) => {
  const limit = query.limit || 50;
  const queueType = query.type;
  return json({
    matches: [],
    limit,
    queueType,
    message: 'Matches endpoint - database connection required',
  }, { headers: corsHeaders });
});

router.get('/matches/:matchId', async ({ params }) => {
  const { matchId } = params;
  return json({
    matchId,
    message: `Match ${matchId} details`,
  }, { headers: corsHeaders });
});

router.get('/league/matches', async ({ query }) => {
  const limit = query.limit || 50;
  const queueType = query.type;
  return json({
    matches: [],
    limit,
    queueType,
    message: 'League matches endpoint - database connection required',
  }, { headers: corsHeaders });
});

// ==================== Drafts ====================

router.get('/draft/sessions', async () => {
  return json({
    sessions: [],
    message: 'Draft sessions - database connection required',
  }, { headers: corsHeaders });
});

router.get('/draft/sessions/:sessionId', async ({ params }) => {
  const { sessionId } = params;
  return json({
    sessionId,
    message: `Draft session ${sessionId}`,
  }, { headers: corsHeaders });
});

router.post('/draft/sessions', async (request) => {
  const data = await request.json();
  return json({
    success: true,
    sessionId: `session_${Date.now()}`,
    message: 'Draft session created',
    data,
  }, { headers: corsHeaders, status: 201 });
});

router.post('/draft/sessions/:sessionId/action', async ({ params }, request) => {
  const { sessionId } = params;
  const action = await request.json();
  return json({
    success: true,
    sessionId,
    action,
    message: 'Draft action executed',
  }, { headers: corsHeaders });
});

router.get('/draft/sessions/:sessionId/history', async ({ params }) => {
  const { sessionId } = params;
  return json({
    sessionId,
    history: [],
    message: `Draft history for session ${sessionId}`,
  }, { headers: corsHeaders });
});

// ==================== Collection ====================

router.post('/collect', async () => {
  return json({
    success: true,
    message: 'Match collection started',
  }, { headers: corsHeaders, status: 202 });
});

router.post('/collect/team/:teamId', async ({ params }) => {
  const { teamId } = params;
  return json({
    success: true,
    teamId,
    message: `Team ${teamId} match collection started`,
  }, { headers: corsHeaders, status: 202 });
});

// ==================== Champions ====================

router.get('/champions', async () => {
  return json({
    champions: [],
    message: 'Champions list - static data required',
  }, { headers: corsHeaders });
});

router.get('/champions/:championId', async ({ params }) => {
  const { championId } = params;
  return json({
    championId,
    message: `Champion ${championId} details`,
  }, { headers: corsHeaders });
});

// ==================== Admin ====================

router.post('/admin/login', async (request) => {
  const data = await request.json();
  return json({
    success: false,
    message: 'Admin login requires proper authentication setup',
  }, { headers: corsHeaders, status: 401 });
});

// 404 handler
router.all('*', () => {
  return error(404, 'Not Found');
});

// Worker fetch handler
export default {
  async fetch(request, env, ctx) {
    return router.handle(request, env, ctx);
  },
};
