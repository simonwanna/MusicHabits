from __future__ import annotations

import csv
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.data_processor import MonthlySnapshot

DEFAULT_HISTORY_PATH = Path(os.environ.get("LISTENING_HISTORY_PATH", "site/listening_history.csv"))
CSV_HEADERS = [
    "month_key",
    "month_label",
    "generated_at",
    "artist_name",
    "playcount",
    "image_url",
    "url",
    "rank",
]


def _ensure_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _snapshot_to_payload(snapshot: MonthlySnapshot) -> Dict[str, Any]:
    return {
        "month_key": snapshot.month_key,
        "month_label": snapshot.month_label,
        "generated_at": snapshot.generated_at,
        "artists": [asdict(artist) for artist in snapshot.artists],
    }


def load_history(history_path: Path = DEFAULT_HISTORY_PATH) -> Dict[str, Dict[str, Any]]:
    """Load the previously saved top 15 artists from the CSV file."""
    if not history_path.exists():
        return {}

    history: Dict[str, Dict[str, Any]] = {}
    with history_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            month_key = row["month_key"]
            bucket = history.setdefault(
                month_key,
                {
                    "month_key": month_key,
                    "month_label": row["month_label"],
                    "generated_at": row["generated_at"],
                    "artists": [],
                },
            )

            bucket["artists"].append(
                {
                    "name": row["artist_name"],
                    "playcount": int(row["playcount"]),
                    "image_url": row["image_url"] or None,
                    "url": row["url"] or None,
                    "rank": int(row["rank"]),
                }
            )

    return dict(sorted(history.items(), key=lambda item: item[0]))


def save_data(snapshot: MonthlySnapshot, history_path: Path = DEFAULT_HISTORY_PATH) -> Dict[str, Dict[str, Any]]:
    """
    Persist the snapshot and return the full listening history.
    Args:
        snapshot: MonthlySnapshot to be saved, the current month's artist data.
        history_path: Path to the CSV file where history is stored from the previous months.
    Returns:
        Ordered dict of month_key -> snapshot payload.
    """
    history = load_history(history_path)
    history[snapshot.month_key] = _snapshot_to_payload(snapshot)
    ordered_history = dict(sorted(history.items(), key=lambda item: item[0]))
    _write_history(ordered_history.values(), history_path)
    return ordered_history


def _write_history(snapshots: Iterable[Dict[str, Any]], history_path: Path) -> None:
    _ensure_directory(history_path)
    with history_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for snapshot in sorted(snapshots, key=lambda snap: snap["month_key"]):
            artists: List[Dict[str, Any]] = sorted(
                snapshot["artists"],
                key=lambda artist: (artist.get("rank", 0), -artist.get("playcount", 0)),
            )
            for artist in artists:
                writer.writerow(
                    {
                        "month_key": snapshot["month_key"],
                        "month_label": snapshot["month_label"],
                        "generated_at": snapshot["generated_at"],
                        "artist_name": artist["name"],
                        "playcount": artist["playcount"],
                        "image_url": artist.get("image_url") or "",
                        "url": artist.get("url") or "",
                        "rank": artist.get("rank", 0),
                    }
                )
