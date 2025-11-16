from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

MAX_ARTISTS = 15


@dataclass
class ArtistStat:
    name: str
    playcount: int
    image_url: Optional[str]  # TODO: remove
    url: Optional[str]
    rank: int


@dataclass
class MonthlySnapshot:
    month_key: str
    month_label: str
    generated_at: str
    artists: List[ArtistStat]


def process_data(raw_data: Dict[str, Any], run_timestamp: Optional[datetime] = None) -> MonthlySnapshot:
    """
    Turn the Last.fm payload into a normalized monthly snapshot.

    Args:
        raw_data: Response returned by `fetch_top_artists`.
        run_timestamp: Optional timestamp that should be used to label the month.

    Returns:
        MonthlySnapshot: structured data ready for persistence + UI updates.
    """
    if run_timestamp is None:
        run_timestamp = datetime.now(tz=timezone.utc)

    month_key = run_timestamp.strftime("%Y-%m")
    month_label = run_timestamp.strftime("%B %Y")
    generated_at = run_timestamp.isoformat()

    artist_entries = (raw_data or {}).get("topartists", {}).get("artist", [])
    artist_entries = artist_entries[:MAX_ARTISTS]

    artists: List[ArtistStat] = []
    for rank, artist_payload in enumerate(artist_entries, start=1):
        name = str(artist_payload.get("name") or f"Artist {rank}")
        try:
            playcount = int(artist_payload.get("playcount") or 0)
        except (TypeError, ValueError):
            playcount = 0

        artists.append(
            ArtistStat(
                name=name,
                playcount=playcount,
                image_url=None,
                url=artist_payload.get("url"),
                rank=rank,
            )
        )

    # Keep deterministic ordering for downstream processing
    artists.sort(key=lambda a: (a.rank, -a.playcount, a.name.lower()))

    return MonthlySnapshot(
        month_key=month_key,
        month_label=month_label,
        generated_at=generated_at,
        artists=artists,
    )
