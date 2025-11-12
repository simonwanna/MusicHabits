from datetime import datetime, timezone

from app.data_processor import process_data


def _make_payload() -> dict:
    return {
        "topartists": {
            "artist": [
                {
                    "name": "Artist A",
                    "playcount": "42",
                    "url": "https://example.com/a",
                    "image": [
                        {"size": "small", "#text": "small_a.jpg"},
                        {"size": "large", "#text": "large_a.jpg"},
                    ],
                },
                {
                    "name": "Artist B",
                    "playcount": "7",
                    "url": "https://example.com/b",
                    "image": [],
                },
            ]
        }
    }


def test_process_data_normalizes_month_and_artists() -> None:
    run_at = datetime(2024, 2, 15, 12, 0, tzinfo=timezone.utc)
    snapshot = process_data(_make_payload(), run_timestamp=run_at)

    assert snapshot.month_key == "2024-02"
    assert snapshot.month_label == "February 2024"
    assert snapshot.generated_at.startswith("2024-02-15T12:00")
    assert len(snapshot.artists) == 2

    top_artist = snapshot.artists[0]
    assert top_artist.name == "Artist A"
    assert top_artist.playcount == 42
    # assert top_artist.image_url == "large_a.jpg"  # TODO implement after Spotipy fetch is added
