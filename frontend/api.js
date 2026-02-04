// League Tracker - API Module
// This module handles all API communication with the serverless backend

// API base URL configuration
// For local development: use '/api' (proxy) or 'http://localhost:3000'
// For production: set API_URL environment variable or use window.API_URL
const getApiBaseUrl = () => {
  // Check for environment variable (set by build/deployment process)
  if (typeof API_URL !== 'undefined') return API_URL;
  
  // Check for window-level configuration (set by deployment)
  if (typeof window !== 'undefined' && window.API_URL) return window.API_URL;
  
  // Check for query parameter (useful for testing different environments)
  const params = new URLSearchParams(window.location.search);
  if (params.has('api')) return params.get('api');
  
  // Default to relative path (for local development with proxy)
  return '/api';
};

class LeagueAPI {
    constructor(baseUrl = null) {
        this.baseUrl = baseUrl || getApiBaseUrl();
    }

    // Generic fetch wrapper with error handling
    async fetch(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: 'Request failed' }));
                throw new Error(error.error || error.message || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    // ==================== Teams ====================

    async getTeams() {
        return this.fetch('/teams');
    }

    async getTeam(teamId) {
        return this.fetch(`/teams/${teamId}`);
    }

    async registerTeam(teamName, players) {
        return this.fetch('/teams/register', {
            method: 'POST',
            body: JSON.stringify({ team_name: teamName, players })
        });
    }

    // ==================== Players ====================

    async getPlayer(puuid) {
        return this.fetch(`/players/${puuid}`);
    }

    async getPlayerMatches(puuid) {
        return this.fetch(`/players/${puuid}/matches`);
    }

    async getPlayerStats(puuid) {
        return this.fetch(`/players/${puuid}/stats`);
    }

    // ==================== Matches ====================

    async getMatches(limit = 50, queueType = null) {
        const params = new URLSearchParams({ limit });
        if (queueType) params.append('type', queueType);
        return this.fetch(`/league/matches?${params}`);
    }

    async getMatch(matchId) {
        return this.fetch(`/matches/${matchId}`);
    }

    // ==================== Drafts ====================

    async getDraftSessions() {
        return this.fetch('/draft/sessions');
    }

    async getDraftSession(sessionId) {
        return this.fetch(`/draft/sessions/${sessionId}`);
    }

    async createDraftSession(data) {
        return this.fetch('/draft/sessions', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async executeDraftAction(sessionId, action) {
        return this.fetch(`/draft/sessions/${sessionId}/action`, {
            method: 'POST',
            body: JSON.stringify(action)
        });
    }

    async getDraftHistory(sessionId) {
        return this.fetch(`/draft/sessions/${sessionId}/history`);
    }

    // ==================== Collection ====================

    async collectMatches() {
        return this.fetch('/collect', { method: 'POST' });
    }

    async collectTeamMatches(teamId) {
        return this.fetch(`/collect/team/${teamId}`, { method: 'POST' });
    }

    // ==================== Champions ====================

    async getChampions() {
        return this.fetch('/champions');
    }

    async getChampion(championId) {
        return this.fetch(`/champions/${championId}`);
    }

    // ==================== Admin ====================

    async adminLogin(username, password) {
        return this.fetch('/admin/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    }
}

// Export singleton instance
window.leagueAPI = new LeagueAPI();

// Export class for custom instances
window.LeagueAPI = LeagueAPI;
