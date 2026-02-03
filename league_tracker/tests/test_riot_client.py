"""
Unit tests for Riot API client.
"""
import pytest
from unittest.mock import Mock, patch

from src.api.riot_client import RiotClient, RiotAPIError


@pytest.mark.unit
class TestRiotClient:
    """Tests for RiotClient class."""

    @pytest.fixture
    def client(self, mock_riot_api_key):
        """Create a RiotClient instance for testing."""
        return RiotClient(api_key='test-api-key')

    def test_init_with_api_key(self, mock_riot_api_key):
        """Test client initialization with API key."""
        client = RiotClient(api_key='test-api-key')
        assert client.api_key == 'test-api-key'

    def test_init_without_api_key(self, monkeypatch):
        """Test client initialization fails without API key."""
        # Unset the RIOT_API_KEY environment variable to test the error case
        monkeypatch.delenv('RIOT_API_KEY', raising=False)
        with pytest.raises(RiotAPIError, match='Riot API key is required'):
            RiotClient(api_key=None)

    def test_get_regional_route_na(self, client):
        """Test regional routing for NA regions."""
        assert client._get_regional_route('na1') == 'americas'
        assert client._get_regional_route('NA1') == 'americas'
        assert client._get_regional_route('br1') == 'americas'
        assert client._get_regional_route('lan') == 'americas'
        assert client._get_regional_route('las') == 'americas'

    def test_get_regional_route_eu(self, client):
        """Test regional routing for EU regions."""
        assert client._get_regional_route('euw1') == 'europe'
        assert client._get_regional_route('eun1') == 'europe'
        assert client._get_regional_route('tr1') == 'europe'
        assert client._get_regional_route('ru') == 'europe'

    def test_get_regional_route_asia(self, client):
        """Test regional routing for Asia regions."""
        assert client._get_regional_route('kr') == 'asia'
        assert client._get_regional_route('jp1') == 'asia'
        assert client._get_regional_route('sea') == 'asia'

    def test_get_regional_route_invalid(self, client):
        """Test regional routing with invalid region."""
        with pytest.raises(ValueError, match='Unsupported or invalid region'):
            client._get_regional_route('invalid')

    def test_get_regional_route_empty(self, client):
        """Test regional routing with empty region."""
        with pytest.raises(ValueError, match='Region must be a non-empty string'):
            client._get_regional_route('')

    @patch('src.api.riot_client.requests.request')
    def test_make_request_success(self, mock_request, client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"test": "data"}'
        mock_response.json.return_value = {'test': 'data'}
        mock_request.return_value = mock_response

        result = client._make_request('https://test.api.com')
        assert result == {'test': 'data'}
        mock_request.assert_called_once()

    @patch('src.api.riot_client.requests.request')
    def test_make_request_error(self, mock_request, client):
        """Test API request with error status."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'Not Found'
        mock_request.return_value = mock_response

        with pytest.raises(RiotAPIError, match='API request failed: 404'):
            client._make_request('https://test.api.com')

    @patch('src.api.riot_client.requests.request')
    def test_make_request_empty_response(self, mock_request, client):
        """Test API request with empty response (200 status with empty text)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ''
        mock_request.return_value = mock_response

        result = client._make_request('https://test.api.com')
        assert result == {}

    @patch('src.api.riot_client.RiotClient._make_request')
    def test_get_puuid_from_riot_id_success(self, mock_request, client):
        """Test getting PUUID from Riot ID successfully."""
        mock_request.return_value = {'puuid': 'test-puuid-12345'}

        result = client.get_puuid_from_riot_id('TestPlayer', 'NA1', 'na1')
        assert result == 'test-puuid-12345'

    @patch('src.api.riot_client.RiotClient._make_request')
    def test_get_puuid_from_riot_id_failure(self, mock_request, client):
        """Test getting PUUID from Riot ID on failure."""
        mock_request.side_effect = RiotAPIError('API request failed: 404')

        result = client.get_puuid_from_riot_id('TestPlayer', 'NA1', 'na1')
        assert result is None

    @patch('src.api.riot_client.requests.get')
    def test_get_match_ids_by_puuid(self, mock_get, client):
        """Test getting match IDs by PUUID."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = ['match1', 'match2', 'match3']
        mock_get.return_value = mock_response

        result = client.get_match_ids_by_puuid('test-puuid', 'na1', count=3)
        assert result == ['match1', 'match2', 'match3']
        mock_get.assert_called_once()

    @patch('src.api.riot_client.requests.get')
    def test_get_match_ids_with_queue_filter(self, mock_get, client):
        """Test getting match IDs with queue filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = ['match1']
        mock_get.return_value = mock_response

        result = client.get_match_ids_by_puuid(
            'test-puuid', 'na1', count=10, queue=420
        )
        assert result == ['match1']

    @patch('src.api.riot_client.requests.get')
    def test_get_match_ids_error(self, mock_get, client):
        """Test getting match IDs on error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        with pytest.raises(RiotAPIError, match='Failed to get match IDs'):
            client.get_match_ids_by_puuid('test-puuid', 'na1')

    @patch('src.api.riot_client.RiotClient._make_request')
    def test_get_match_details(self, mock_request, client):
        """Test getting match details."""
        mock_request.return_value = {
            'metadata': {'matchId': 'NA1_1234567890'},
            'info': {'gameDuration': 1800}
        }

        result = client.get_match_details('NA1_1234567890', 'na1')
        assert result['metadata']['matchId'] == 'NA1_1234567890'
        assert result['info']['gameDuration'] == 1800

    @patch('src.api.riot_client.RiotClient._make_request')
    def test_get_match_timeline(self, mock_request, client):
        """Test getting match timeline."""
        mock_request.return_value = {'frames': []}

        result = client.get_match_timeline('NA1_1234567890', 'na1')
        assert result == {'frames': []}

    @patch('src.api.riot_client.RiotClient._make_request')
    def test_get_summoner_by_puuid(self, mock_request, client):
        """Test getting summoner by PUUID."""
        mock_request.return_value = {
            'id': 'summoner-id',
            'name': 'TestPlayer',
            'puuid': 'test-puuid'
        }

        result = client.get_summoner_by_puuid('test-puuid', 'na1')
        assert result['name'] == 'TestPlayer'
        assert result['puuid'] == 'test-puuid'
