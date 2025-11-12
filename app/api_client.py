import requests


def fetch_top_artists(api_key: str, user: str, period: str = "1month", limit: int = 15, page: int = 1) -> dict:
    """Fetches the top artists for a given Last.fm user over a specified time period."""
    endpoint = "https://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "user.gettopartists",
        "user": user,
        "api_key": api_key,
        "period": period,  # overall | 7day | 1month | 3month | 6month | 12month
        "limit": limit,
        "page": page,
        "format": "json",
    }
    r = requests.get(endpoint, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"Last.fm error {data['error']}: {data['message']}")
    return data
