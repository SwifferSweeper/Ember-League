"""
Unit tests for Flask application routes.
"""
import pytest
from flask import session


@pytest.mark.unit
class TestIndexRoutes:
    """Tests for index and basic routes."""

    def test_index_route(self, client):
        """Test index route."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'League Tracker' in response.data

    def test_teams_list_route(self, client):
        """Test teams list route."""
        response = client.get('/teams')
        assert response.status_code == 200

    def test_leaderboards_route(self, client):
        """Test leaderboards route."""
        response = client.get('/leaderboards')
        assert response.status_code == 200

    def test_league_matches_route(self, client):
        """Test league matches route."""
        response = client.get('/league/matches')
        assert response.status_code == 200


@pytest.mark.unit
class TestTeamRoutes:
    """Tests for team-related routes."""

    def test_team_detail_route(self, client, sample_team):
        """Test team detail route."""
        response = client.get(f'/teams/{sample_team.id}')
        assert response.status_code == 200

    def test_team_detail_not_found(self, client):
        """Test team detail route with non-existent team."""
        response = client.get('/teams/999999')
        assert response.status_code == 404


@pytest.mark.unit
class TestMatchRoutes:
    """Tests for match-related routes."""

    def test_match_detail_route(self, client, sample_match):
        """Test match detail route."""
        response = client.get(f'/matches/{sample_match.match_id}')
        assert response.status_code == 200

    def test_match_detail_not_found(self, client):
        """Test match detail route with non-existent match."""
        response = client.get('/matches/NA1_9999999999')
        assert response.status_code == 404


@pytest.mark.unit
class TestSignupRoutes:
    """Tests for signup routes."""

    def test_signup_get(self, client):
        """Test signup GET route."""
        response = client.get('/signup')
        assert response.status_code == 200

    def test_signup_post_valid(self, client, db_session):
        """Test signup POST with valid data."""
        response = client.post('/signup', data={
            'team_name': 'New Team',
            'player_name[]': ['Player1'],
            'player_tag[]': ['NA1'],
            'player_region[]': ['na1']
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_signup_post_missing_name(self, client):
        """Test signup POST with missing team name."""
        response = client.post('/signup', data={
            'player_name[]': ['Player1'],
            'player_tag[]': ['NA1'],
            'player_region[]': ['na1']
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'required' in response.data.lower()


@pytest.mark.unit
class TestAdminRoutes:
    """Tests for admin routes."""

    def test_admin_login_get(self, client):
        """Test admin login GET route."""
        response = client.get('/admin/login')
        assert response.status_code == 200

    def test_admin_login_valid(self, client, sample_admin):
        """Test admin login with valid credentials."""
        response = client.post('/admin/login', data={
            'username': sample_admin.username,
            'password': 'test_password'
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_admin_login_invalid(self, client, sample_admin):
        """Test admin login with invalid credentials."""
        response = client.post('/admin/login', data={
            'username': sample_admin.username,
            'password': 'wrong_password'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'invalid' in response.data.lower()

    def test_admin_logout(self, client, sample_admin):
        """Test admin logout route."""
        with client.session_transaction() as sess:
            sess['admin_id'] = sample_admin.id

        response = client.get('/admin/logout', follow_redirects=True)
        assert response.status_code == 200

    def test_admin_dashboard_unauthorized(self, client):
        """Test admin dashboard without login."""
        response = client.get('/admin/dashboard')
        assert response.status_code == 302  # Redirect to login

    def test_admin_dashboard_authorized(self, authenticated_client):
        """Test admin dashboard with login."""
        response = authenticated_client.get('/admin/dashboard')
        assert response.status_code == 200


@pytest.mark.unit
class TestDraftRoutes:
    """Tests for draft-related routes."""

    def test_draft_index(self, client):
        """Test draft index route."""
        response = client.get('/draft')
        assert response.status_code == 200

    def test_draft_create_get(self, client):
        """Test draft create GET route."""
        response = client.get('/draft/create')
        assert response.status_code == 200

    def test_draft_view(self, client, sample_draft_session):
        """Test draft view route."""
        response = client.get(f'/draft/{sample_draft_session.id}')
        assert response.status_code == 200

    def test_draft_view_not_found(self, client):
        """Test draft view with non-existent session."""
        response = client.get('/draft/999999')
        assert response.status_code == 404

    def test_draft_history(self, client, sample_draft_session):
        """Test draft history route."""
        response = client.get(f'/draft/{sample_draft_session.id}/history')
        assert response.status_code == 200


@pytest.mark.unit
class TestAPIRoutes:
    """Tests for API routes."""

    def test_api_teams(self, client):
        """Test API teams endpoint."""
        response = client.get('/api/teams')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_api_team_detail(self, client, sample_team):
        """Test API team detail endpoint."""
        response = client.get(f'/api/teams/{sample_team.id}')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_api_team_detail_not_found(self, client):
        """Test API team detail with non-existent team."""
        response = client.get('/api/teams/999999')
        assert response.status_code == 404

    def test_api_register_team_valid(self, client, db_session):
        """Test API register team with valid data."""
        response = client.post('/api/teams/register', json={
            'team_name': 'API Team',
            'players': [
                {
                    'game_name': 'Player1',
                    'tag_line': 'NA1',
                    'region': 'na1'
                }
            ]
        }, content_type='application/json')
        assert response.status_code == 201
        assert response.content_type == 'application/json'

    def test_api_register_team_missing_data(self, client):
        """Test API register team with missing data."""
        response = client.post('/api/teams/register', json={},
                          content_type='application/json')
        assert response.status_code == 400

    def test_api_draft_sessions(self, client):
        """Test API draft sessions endpoint."""
        response = client.get('/api/draft/sessions')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_api_draft_session(self, client, sample_draft_session):
        """Test API draft session endpoint."""
        response = client.get(f'/api/draft/sessions/{sample_draft_session.id}')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_api_draft_session_not_found(self, client):
        """Test API draft session with non-existent session."""
        response = client.get('/api/draft/sessions/999999')
        assert response.status_code == 404

    def test_api_champions(self, client):
        """Test API champions endpoint."""
        response = client.get('/api/champions')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_api_champion(self, client):
        """Test API champion endpoint."""
        response = client.get('/api/champions/1')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_api_champion_not_found(self, client):
        """Test API champion with non-existent champion."""
        response = client.get('/api/champions/999999')
        assert response.status_code == 404


@pytest.mark.unit
class TestErrorHandlers:
    """Tests for error handlers."""

    def test_404_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent-route')
        assert response.status_code == 404
        assert b'not found' in response.data.lower()
