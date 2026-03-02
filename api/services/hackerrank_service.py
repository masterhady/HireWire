import requests
import logging

logger = logging.getLogger(__name__)

class HackerRankService:
    # Using the internal API endpoint often used in challenges as a proxy for public stats if available,
    # or falling back to a basic profile check.
    # Since there is no official public API, we will try to hit a known endpoint that returns some user info.
    # Alternatively, we could scrape the profile page, but that's brittle.
    # For this MVP, we will try a known endpoint.
    
    BASE_URL = "https://www.hackerrank.com/rest/hackers/{}/scores_elo"
    PROFILE_URL = "https://www.hackerrank.com/rest/hackers/{}"

    @staticmethod
    def get_user_stats(username):
        """
        Fetches user statistics from HackerRank.
        Note: This uses undocumented endpoints and might be unstable.
        """
        try:
            # Fetch basic profile info
            profile_response = requests.get(
                HackerRankService.PROFILE_URL.format(username),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json'
                },
                timeout=15
            )
            
            logger.debug(f"HackerRank API response status: {profile_response.status_code}")
            
            if profile_response.status_code == 404:
                logger.warning(f"HackerRank user '{username}' not found")
                return None
                
            profile_response.raise_for_status()
            response_data = profile_response.json()
            profile_data = response_data.get('model', {})
            
            if not profile_data:
                logger.warning(f"No profile data found for HackerRank user '{username}'")
                return None
            
            # Fetch scores/badges if possible (this endpoint might require auth or be limited)
            # For now, we'll stick to what we can get from the profile model
            
            # Construct stats
            parsed_stats = {
                'username': profile_data.get('username', username),
                'name': profile_data.get('name', ''),
                'country': profile_data.get('country', ''),
                'created_at': profile_data.get('created_at', ''),
                'level': profile_data.get('level', 0),
                'total_solved': 0,  # HackerRank doesn't easily expose this
                'easy_solved': 0,
                'medium_solved': 0,
                'hard_solved': 0,
                # HackerRank doesn't easily expose "total solved" in a simple number without scraping
                # We will try to get badges or points if available in the profile model
            }
            
            logger.info(f"Successfully fetched HackerRank profile for {username}")
            return parsed_stats

        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching HackerRank stats for {username}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching HackerRank stats for {username}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching HackerRank stats for {username}: {str(e)}", exc_info=True)
            return None
