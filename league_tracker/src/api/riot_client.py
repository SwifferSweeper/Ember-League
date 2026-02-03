"""
Riot API client wrapper using requests directly.
"""
import logging
from typing import Dict, List, Optional, Any

import requests

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import RIOT_API_KEY, REGIONAL_ROUTING, validate_api_key

logger = logging.getLogger(__name__)


class RiotAPIError(Exception):
    """Custom exception for Riot API errors."""
    pass


class RiotClient:
    """Client for interacting with Riot Games API using requests."""
    
    def __init__(self, api_key: str = None):
        # If api_key is explicitly provided (even as empty string), use it
        # Otherwise, fall back to RIOT_API_KEY from config
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = RIOT_API_KEY
        
        if not self.api_key or self.api_key == "":
            raise RiotAPIError("Riot API key is required. Set RIOT_API_KEY environment variable.")
        
        logger.info("RiotClient initialized with requests")
    
    def _get_regional_route(self, region: str) -> str:
        """
        Get the regional routing cluster for Riot APIs.

        Valid return values:
        - americas
        - europe
        - asia

        Raises:
            ValueError if the region cannot be mapped.
        """
        if not region:
            raise ValueError("Region must be a non-empty string")
        
        print(region)
        region_lower = region.lower()

        if region_lower.startswith(("na", "br", "lan", "las")):
            return "americas"

        if region_lower.startswith(("euw", "eun", "tr", "ru")):
            return "europe"

        if region_lower.startswith(("kr", "jp", "sea")):
            # SEA Riot IDs live on the ASIA regional cluster
            return "asia"

        raise ValueError(
            f"Unsupported or invalid region '{region}'. "
            "Expected a platform tag like NA1, EUW1, KR, JP, SEA, etc."
        )

    
    def _make_request(self, url: str, method: str = "GET") -> Dict[str, Any]:
        """Make a request to the Riot API."""
        headers = {"X-Riot-Token": self.api_key}
        response = requests.request(method, url, headers=headers)
        
        if response.status_code not in (200, 201):
            logger.error(f"API Error: {response.status_code} - {response.text}")
            raise RiotAPIError(f"API request failed: {response.status_code}")
        
        if response.text:
            return response.json()
        return {}
    
    def get_puuid_from_riot_id(self, game_name: str, tag_line: str, region: str) -> Optional[str]:
        """
        Get PUUID from a player's Riot ID.
        
        Args:
            game_name: Player's in-game name
            tag_line: Player's tag (e.g., NA1)
            region: Player's selected region (e.g., na1, euw1)
            
        Returns:
            PUUID string or None if not found
        """
        try:
            # Use the player's selected region for regional routing
            regional = self._get_regional_route(region)
            url = f"https://{regional}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
            print(url)
            account = self._make_request(url)
            return account.get('puuid')
        except RiotAPIError:
            return None
    
    def get_match_ids_by_puuid(self, puuid: str, region: str = "americas",
                               count: int = 20, queue: int = None) -> List[str]:
        """
        Get match IDs for a player by PUUID.
        """
        try:
            regional = self._get_regional_route(region)
            url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
            params = {'start': 0, 'count': min(count, 100)}
            if queue:
                params['queue'] = queue
            
            headers = {"X-Riot-Token": self.api_key}
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                logger.error(f"API Error getting match IDs: {response.status_code}")
                raise RiotAPIError(f"Failed to get match IDs: {response.status_code}")
            
            return response.json()
        except Exception as e:
            logger.error(f"Error getting match IDs: {e}")
            raise RiotAPIError(f"Failed to get match IDs: {e}")
    
    def get_match_details(self, match_id: str, region: str = "americas") -> Dict[str, Any]:
        """
        Get detailed match information by match ID.
        """
        try:
            regional = self._get_regional_route(region)
            url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            return self._make_request(url)
        except Exception as e:
            logger.error(f"Error getting match: {e}")
            raise RiotAPIError(f"Failed to get match: {e}")
    
    def get_match_timeline(self, match_id: str, region: str = "americas") -> Dict[str, Any]:
        """
        Get match timeline data.
        """
        try:
            regional = self._get_regional_route(region)
            url = f"https://{regional}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
            return self._make_request(url)
        except Exception as e:
            logger.error(f"Error getting timeline: {e}")
            raise RiotAPIError(f"Failed to get timeline: {e}")
    
    def get_summoner_by_puuid(self, puuid: str, region: str) -> Dict[str, Any]:
        """
        Get summoner information by PUUID.
        """
        try:
            url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
            return self._make_request(url)
        except Exception as e:
            logger.error(f"Error getting summoner: {e}")
            raise RiotAPIError(f"Failed to get summoner: {e}")
