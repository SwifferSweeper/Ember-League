import os
import json
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from cloudflare_workers import Request, Response

# Import configuration
from config import config

class RiotAPIError(Exception):
    """Custom exception for Riot API errors."""
    pass

class RiotClient:
    """Riot API client for Cloudflare Workers."""
    
    def __init__(self):
        self.api_key = config.RIOT_API_KEY
        self.base_url = "https://americas.api.riotgames.com"
        self.regional_routing = {
            "americas": "americas",
            "europe": "europe",
            "asia": "asia",
            "sea": "sea"
        }
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the Riot API."""
        if not self.api_key:
            raise RiotAPIError("No API key configured")
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "X-Riot-Token": self.api_key,
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {}
            else:
                raise RiotAPIError(f"API request failed: {response.status_code} - {response.text}")
        except Exception as e:
            raise RiotAPIError(f"Request error: {str(e)}")
    
    def get_puuid_from_riot_id(self, game_name: str, tag_line: str, region: str) -> Optional[str]:
        """Get PUUID from Riot ID."""
        endpoint = f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        params = {"region": self.regional_routing.get(region, "americas")}
        
        try:
            data = self._make_request(endpoint, params)
            return data.get("puuid")
        except RiotAPIError:
            return None
    
    def get_summoner_by_puuid(self, puuid: str, region: str) -> Optional[Dict[str, Any]]:
        """Get summoner data by PUUID."""
        endpoint = f"/riot/summoner/v4/summoners/by-puuid/{puuid}"
        params = {"region": self.regional_routing.get(region, "americas")}
        
        try:
            return self._make_request(endpoint, params)
        except RiotAPIError:
            return None
    
    def get_matchlist(self, puuid: str, region: str, queue: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """Get matchlist for a player."""
        endpoint = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {
            "region": self.regional_routing.get(region, "americas"),
            "queue": queue,
            "count": count
        }
        
        try:
            match_ids = self._make_request(endpoint, params)
            matches = []
            for match_id in match_ids:
                match = self.get_match(match_id, region)
                if match:
                    matches.append(match)
            return matches
        except RiotAPIError:
            return []
    
    def get_match(self, match_id: str, region: str) -> Optional[Dict[str, Any]]:
        """Get match details."""
        endpoint = f"/lol/match/v5/matches/{match_id}"
        params = {"region": self.regional_routing.get(region, "americas")}
        
        try:
            return self._make_request(endpoint, params)
        except RiotAPIError:
            return None
    
    def get_tournament_codes(self, count: int, tournament_id: int, team_size: int = 5) -> List[str]:
        """Generate tournament codes."""
        endpoint = "/lol/tournament/v5/codes"
        params = {
            "count": count,
            "tournamentId": tournament_id,
            "teamSize": team_size,
            "mapType": "SUMMONERS_RIFT",
            "pickType": "TOURNAMENT_DRAFT",
            "spectatorType": "ALL",
            "lobbyName": "League Tracker Tournament"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers={"X-Riot-Token": self.api_key},
                json=params
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise RiotAPIError(f"Tournament code generation failed: {response.status_code}")
        except Exception as e:
            raise RiotAPIError(f"Tournament code error: {str(e)}")

# Global Riot client instance
riot_client = RiotClient()

def get_riot_client() -> Optional[RiotClient]:
    """Get the Riot client instance."""
    if config.validate_api_key():
        return riot_client
    return None