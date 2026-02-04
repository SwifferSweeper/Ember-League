// League Tracker - Environment Configuration
// This file is generated during deployment. DO NOT commit with actual values.

(function() {
  'use strict';

  // Configuration object
  window.LEAGUE_TRACKER_CONFIG = {
    // API Configuration
    API_URL: '', // Set this to your Cloudflare Workers URL for production
    
    // Feature Flags
    ENABLE_DRAFTS: true,
    ENABLE_MATCH_COLLECTION: false,
    ENABLE_ADMIN: false,
    
    // App Info
    VERSION: '1.0.0',
    ENVIRONMENT: 'development', // 'development' or 'production'
  };

  // Override with environment variable if available (for build-time injection)
  if (typeof API_URL !== 'undefined') {
    window.LEAGUE_TRACKER_CONFIG.API_URL = API_URL;
  }

  // Detect environment based on hostname
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      window.LEAGUE_TRACKER_CONFIG.ENVIRONMENT = 'development';
    } else {
      window.LEAGUE_TRACKER_CONFIG.ENVIRONMENT = 'production';
    }
  }

  // Set API_URL from config if not already set
  if (!window.LEAGUE_TRACKER_CONFIG.API_URL && typeof window !== 'undefined') {
    // In production, the API URL would be set during deployment
    // For local development, you can use a query parameter: ?api=http://localhost:3000
    const params = new URLSearchParams(window.location.search);
    if (params.has('api')) {
      window.LEAGUE_TRACKER_CONFIG.API_URL = params.get('api');
    }
  }
})();
