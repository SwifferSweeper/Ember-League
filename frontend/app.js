// League Tracker - Main Application

document.addEventListener('DOMContentLoaded', function() {
    console.log('League Tracker initialized');
    
    // Initialize page-specific functionality
    initPage();
});

function initPage() {
    const path = window.location.pathname;
    const page = path.split('/').pop() || 'index.html';
    
    switch(page) {
        case 'index.html':
            initHomePage();
            break;
        case 'teams.html':
            initTeamsPage();
            break;
        case 'matches.html':
            initMatchesPage();
            break;
        case 'leaderboards.html':
            initLeaderboardsPage();
            break;
        case 'draft.html':
            initDraftPage();
            break;
    }
}

// ==================== Home Page ====================

async function initHomePage() {
    try {
        // Load stats
        await loadStats();
        await loadRecentTeams();
    } catch (error) {
        console.error('Error loading home page:', error);
        showError('Failed to load data');
    }
}

async function loadStats() {
    try {
        const teams = await leagueAPI.getTeams();
        
        document.getElementById('total-teams').textContent = teams.length || 0;
        
        // Calculate total players
        let totalPlayers = 0;
        teams.forEach(team => {
            totalPlayers += team.player_count || 0;
        });
        document.getElementById('total-players').textContent = totalPlayers;
        
        // For matches, we'd need to fetch from the API
        document.getElementById('total-matches').textContent = '-';
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadRecentTeams() {
    const container = document.getElementById('recent-teams');
    container.innerHTML = '<div class="loading">Loading teams...</div>';
    
    try {
        const teams = await leagueAPI.getTeams();
        
        if (teams.length === 0) {
            container.innerHTML = '<p>No teams found. <a href="#">Register a team</a> to get started!</p>';
            return;
        }
        
        // Show last 5 teams
        const recentTeams = teams.slice(0, 5);
        
        container.innerHTML = `
            <div class="teams-grid">
                ${recentTeams.map(team => renderTeamCard(team)).join('')}
            </div>
        `;
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load teams: ${error.message}</div>`;
    }
}

// ==================== Teams Page ====================

async function initTeamsPage() {
    const container = document.getElementById('teams-list');
    container.innerHTML = '<div class="loading">Loading teams...</div>';
    
    try {
        const teams = await leagueAPI.getTeams();
        
        if (teams.length === 0) {
            container.innerHTML = '<p>No teams found. Register a team to get started!</p>';
            return;
        }
        
        container.innerHTML = `
            <div class="teams-grid">
                ${teams.map(team => renderTeamCard(team)).join('')}
            </div>
        `;
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load teams: ${error.message}</div>`;
    }
}

function renderTeamCard(team) {
    return `
        <div class="team-card" onclick="window.location.href='team.html?id=${team.id}'">
            <div class="team-name">${escapeHtml(team.name)}</div>
            <div class="team-players">${team.player_count || 0} players</div>
        </div>
    `;
}

// ==================== Utility Functions ====================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    console.error(message);
}

function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}
