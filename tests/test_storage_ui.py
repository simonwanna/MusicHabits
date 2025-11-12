from datetime import datetime, timezone
from pathlib import Path

from app.data_processor import ArtistStat, MonthlySnapshot
from app.storage import save_data
from app.ui_updater import _prepare_snapshots, update_ui


def _snapshot(month: str, playcount: int) -> MonthlySnapshot:
    """A snapshot is a month's worth of artist stats."""
    run_date = datetime.strptime(month + "-15T12:00:00+00:00", "%Y-%m-%dT%H:%M:%S+00:00").replace(tzinfo=timezone.utc)
    return MonthlySnapshot(
        month_key=month,
        month_label=run_date.strftime("%B %Y"),
        generated_at=run_date.isoformat(),
        artists=[
            ArtistStat(
                name="Test Artist",
                playcount=playcount,
                image_url="https://example.com/img.png",
                url="https://example.com",
                rank=1,
            )
        ],
    )


def test_save_data_overwrites_existing_month(tmp_path: Path) -> None:
    """Saving the same month twice keeps only the latest playcount."""
    history_path = tmp_path / "history.csv"
    save_data(_snapshot("2024-02", 10), history_path=history_path)
    history = save_data(_snapshot("2024-02", 55), history_path=history_path)

    assert history_path.exists()
    assert len(history) == 1
    latest = history["2024-02"]
    assert latest["artists"][0]["playcount"] == 55


def test_update_ui_builds_html(tmp_path: Path) -> None:
    """UI builder writes an HTML file containing the artist name."""
    history = {
        "2024-02": {
            "month_key": "2024-02",
            "month_label": "February 2024",
            "generated_at": "2024-02-15T12:00:00+00:00",
            "artists": [
                {
                    "name": "Test Artist",
                    "playcount": 42,
                    "image_url": "https://example.com/img.png",
                    "url": "https://example.com",
                    "rank": 1,
                }
            ],
        }
    }
    html_path = update_ui(history, output_dir=tmp_path)
    html = html_path.read_text(encoding="utf-8")

    assert html_path.exists()
    assert "Monthly Top Artists" in html
    assert "Test Artist" in html


def _history_entry(month_key: str, artists: list[dict]) -> dict:
    return {
        "month_key": month_key,
        "month_label": "Label",
        "generated_at": "2024-02-15T12:00:00+00:00",
        "artists": artists,
    }


def _snapshot_colors(snapshot: dict) -> dict[str, str]:
    return {artist["name"]: artist["color"] for artist in snapshot["artists"]}


def test_color_stays_with_artist_across_months() -> None:
    """An artist that remains in the chart keeps the same color each month."""
    history = {
        "2024-02": _history_entry(
            "2024-02",
            [
                {"name": "Repeat Artist", "playcount": 10, "image_url": None, "url": None, "rank": 1},
                {"name": "Other", "playcount": 5, "image_url": None, "url": None, "rank": 2},
            ],
        ),
        "2024-03": _history_entry(
            "2024-03",
            [
                {"name": "Repeat Artist", "playcount": 12, "image_url": None, "url": None, "rank": 1},
                {"name": "Newcomer", "playcount": 7, "image_url": None, "url": None, "rank": 2},
            ],
        ),
    }

    snapshots = _prepare_snapshots(history, {})
    feb_color = next(artist["color"] for artist in snapshots[0]["artists"] if artist["name"] == "Repeat Artist")
    mar_color = next(artist["color"] for artist in snapshots[1]["artists"] if artist["name"] == "Repeat Artist")

    assert feb_color == mar_color


def test_color_is_reused_after_artist_drops() -> None:
    """When an artist leaves, their color becomes available for the next newcomer."""
    history = {
        "2024-02": _history_entry(
            "2024-02",
            [
                {"name": "First", "playcount": 10, "image_url": None, "url": None, "rank": 1},
                {"name": "Second", "playcount": 8, "image_url": None, "url": None, "rank": 2},
            ],
        ),
        "2024-03": _history_entry(
            "2024-03",
            [
                {"name": "First", "playcount": 9, "image_url": None, "url": None, "rank": 1},
                {"name": "Third", "playcount": 6, "image_url": None, "url": None, "rank": 2},
            ],
        ),
    }

    snapshots = _prepare_snapshots(history, {})
    second_color = next(artist["color"] for artist in snapshots[0]["artists"] if artist["name"] == "Second")
    third_color = next(artist["color"] for artist in snapshots[1]["artists"] if artist["name"] == "Third")

    assert second_color == third_color


def test_existing_artists_keep_color_when_order_changes_or_new_artist_added() -> None:
    """Re-running the same month keeps colors even if order changes or a new artist appears."""
    base_history = {
        "2024-02": _history_entry(
            "2024-02",
            [
                {"name": "Alpha", "playcount": 12, "image_url": None, "url": None, "rank": 1},
                {"name": "Gamma", "playcount": 8, "image_url": None, "url": None, "rank": 2},
            ],
        )
    }
    base_snapshots = _prepare_snapshots(base_history, {})
    seed_colors = _snapshot_colors(base_snapshots[0])

    updated_history = {
        "2024-02": _history_entry(
            "2024-02",
            [
                {"name": "Beta", "playcount": 20, "image_url": None, "url": None, "rank": 1},
                {"name": "Alpha", "playcount": 11, "image_url": None, "url": None, "rank": 2},
                {"name": "Gamma", "playcount": 7, "image_url": None, "url": None, "rank": 3},
            ],
        )
    }
    rerun_snapshots = _prepare_snapshots(updated_history, seed_colors)
    rerun_colors = _snapshot_colors(rerun_snapshots[0])

    assert rerun_colors["Alpha"] == seed_colors["Alpha"]
    assert rerun_colors["Gamma"] == seed_colors["Gamma"]
