from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from app.api_client import fetch_top_artists
from app.data_processor import MAX_ARTISTS, process_data
from app.storage import save_data
from app.ui_updater import update_ui

DEFAULT_PERIOD = "1month"


def main() -> None:
    """
    Main entry point for the application.
    It fetches the top artists from Last.fm, processes the data,
    saves it in the CSV file, and updates the UI by comparing to the current month's data
    (if available in json file), it then updates the UI.
    """
    load_dotenv()

    api_key = os.environ.get("LASTFM_API_KEY")
    user = os.environ.get("LASTFM_USER")
    if not api_key or not user:
        raise RuntimeError("LASTFM_API_KEY and LASTFM_USER environment variables are required.")

    lastfm_payload = fetch_top_artists(
        api_key=api_key,
        user=user,
        period=DEFAULT_PERIOD,
        limit=MAX_ARTISTS,
        page=1,
    )

    snapshot = process_data(lastfm_payload, run_timestamp=datetime.now(tz=timezone.utc))
    history = save_data(snapshot)
    update_ui(history)
    print("UI updated successfully.")


if __name__ == "__main__":
    main()
