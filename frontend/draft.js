// League Tracker - Draft Page

async function initDraftPage() {
    await loadDraftSessions();
    await loadTeamsForDraft();
}

async function loadDraftSessions() {
    const activeContainer = document.getElementById('active-drafts');
    const completedContainer = document.getElementById('completed-drafts');
    
    activeContainer.innerHTML = '<div class="loading">Loading active drafts...</div>';
    completedContainer.innerHTML = '<div class="loading">Loading completed drafts...</div>';
    
    try {
        const sessions = await leagueAPI.getDraftSessions();
        
        const active = sessions.filter(s => s.is_active);
        const completed = sessions.filter(s => !s.is_active);
        const all = sessions;
        
        if (active.length === 0) {
            activeContainer.innerHTML = '<p>No active drafts</p>';
        } else {
            activeContainer.innerHTML = active.map(s => renderDraftCard(s)).join('');
        }
        
        if (completed.length === 0) {
            completedContainer.innerHTML = '<p>No completed drafts</p>';
        } else {
            completedContainer.innerHTML = completed.slice(0, 5).map(s => renderDraftCard(s)).join('');
        }
    } catch (error) {
        activeContainer.innerHTML = `<div class="error">Failed to load drafts</div>`;
        completedContainer.innerHTML = `<div class="error">Failed to load drafts</div>`;
    }
}

function renderDraftCard(session) {
    return `
        <div class="team-card" onclick="viewDraft(${session.id})">
            <div class="team-name">${escapeHtml(session.name)}</div>
            <div class="team-players">${session.draft_mode} - Game ${session.current_game_number}</div>
            <div class="team-stats">
                <div class="team-stat">
                    <div class="team-stat-value">${session.current_team_turn?.toUpperCase()}</div>
                    <div class="team-stat-label">Turn</div>
                </div>
            </div>
        </div>
    `;
}

async function loadTeamsForDraft() {
    try {
        const teams = await leagueAPI.getTeams();
        const blueSelect = document.getElementById('team-blue');
        const redSelect = document.getElementById('team-red');
        
        const options = teams.map(t => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join('');
        
        blueSelect.innerHTML = options;
        redSelect.innerHTML = options;
    } catch (error) {
        console.error('Failed to load teams:', error);
    }
}

function createNewDraft() {
    document.getElementById('draft-modal').style.display = 'block';
}

function closeModal() {
    document.getElementById('draft-modal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('draft-modal');
    if (event.target === modal) {
        closeModal();
    }
}

// Handle draft form submission
document.getElementById('draft-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        name: document.getElementById('draft-name').value,
        draft_mode: document.getElementById('draft-mode').value,
        team_blue_id: parseInt(document.getElementById('team-blue').value),
        team_red_id: parseInt(document.getElementById('team-red').value),
        bans_per_team: parseInt(document.getElementById('bans-per-team').value),
        picks_per_team: parseInt(document.getElementById('picks-per-team').value)
    };
    
    if (data.team_blue_id === data.team_red_id) {
        alert('Teams must be different!');
        return;
    }
    
    try {
        const result = await leagueAPI.createDraftSession(data);
        closeModal();
        window.location.href = `draft-view.html?id=${result.session.id}`;
    } catch (error) {
        alert(`Failed to create draft: ${error.message}`);
    }
});

function viewDraft(sessionId) {
    window.location.href = `draft-view.html?id=${sessionId}`;
}
