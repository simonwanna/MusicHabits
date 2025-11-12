from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Iterable, List

from plotly.colors import qualitative

Palette = qualitative.Plotly + qualitative.Safe + qualitative.Bold + qualitative.Pastel + qualitative.Antique


def _default_palette() -> List[str]:
    return list(Palette or ["#3e7cb1", "#f45d48", "#ffd166", "#6a4c93"])


def update_ui(history: Dict[str, Dict[str, Any]], output_dir: Path | str = "site") -> Path:
    """
    Build the static Plotly page along with helper assets.

    Args:
        history: Ordered dict of month_key -> snapshot payload.
        output_dir: Target directory (published via GitHub Pages).
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    seed_colors = _load_existing_colors(output_path / "history.json")

    snapshots = _prepare_snapshots(history, seed_colors)
    html = _render_html(snapshots)
    html_path = output_path / "index.html"
    html_path.write_text(html, encoding="utf-8")

    json_path = output_path / "history.json"
    json_path.write_text(json.dumps(snapshots, indent=2), encoding="utf-8")

    return html_path


def _load_existing_colors(history_json_path: Path) -> Dict[str, str]:
    """Load the previously saved artist colors from the JSON history file."""
    if not history_json_path.exists():
        return {}

    try:
        existing = json.loads(history_json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    colors: Dict[str, str] = {}
    for snapshot in existing:
        for artist in snapshot.get("artists", []):
            name = artist.get("name")
            color = artist.get("color")
            if name and color:
                colors[name] = color
    return colors


def _prepare_snapshots(
    history: Dict[str, Dict[str, Any]],
    seed_colors: Dict[str, str] | None = None,
) -> List[Dict[str, Any]]:
    ordered_snapshots = [history[key] for key in sorted(history.keys())]
    return _attach_consistent_colors(ordered_snapshots, seed_colors or {})


def _attach_consistent_colors(
    snapshots: Iterable[Dict[str, Any]],
    seed_colors: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Attach consistent colors to artists across snapshots."""
    palette = [color for color in _default_palette()]
    free_pool: List[str] = []
    ledger: Dict[str, str] = {name: color for name, color in seed_colors.items() if color}
    active_colors: Dict[str, str] = {}
    in_use = set()

    # Remove already-used colors from palette
    palette = [color for color in palette if color not in ledger.values()]

    decorated_snapshots: List[Dict[str, Any]] = []

    for snapshot in snapshots:
        current_names = [artist["name"] for artist in snapshot["artists"]]
        current_set = set(current_names)

        # Free colors for artists that just dropped out.
        for artist_name in list(active_colors.keys()):
            if artist_name not in current_set:
                color = active_colors.pop(artist_name)
                in_use.discard(color)
                free_pool.append(color)
                ledger.pop(artist_name, None)

        artists = []
        for artist_payload in snapshot["artists"]:
            name = artist_payload["name"]
            if name not in active_colors:
                color = _assign_color(
                    artist_name=name,
                    ledger=ledger,
                    free_pool=free_pool,
                    palette=palette,
                    in_use=in_use,
                )
                active_colors[name] = color
                ledger[name] = color
                in_use.add(color)

            artists.append(
                {
                    "name": name,
                    "playcount": int(artist_payload["playcount"]),
                    "image_url": artist_payload.get("image_url"),
                    "url": artist_payload.get("url"),
                    "rank": artist_payload.get("rank"),
                    "color": active_colors[name],
                }
            )

        decorated_snapshots.append(
            {
                "month_key": snapshot["month_key"],
                "month_label": snapshot["month_label"],
                "generated_at": snapshot["generated_at"],
                "artists": artists,
            }
        )

    return decorated_snapshots


def _assign_color(
    artist_name: str,
    ledger: Dict[str, str],
    free_pool: List[str],
    palette: List[str],
    in_use: set,
) -> str:
    preferred = ledger.get(artist_name)
    if preferred and preferred not in in_use:
        if preferred in free_pool:
            free_pool.remove(preferred)
        elif preferred in palette:
            palette.remove(preferred)
        return preferred

    if free_pool:
        idx = abs(hash(artist_name)) % len(free_pool)
        return free_pool.pop(idx)

    if not palette:
        palette.extend([color for color in _default_palette() if color not in in_use])
        if not palette:
            palette.extend(_default_palette())

    return palette.pop(0)


def _render_html(snapshots: List[Dict[str, Any]]) -> str:
    template_path = resources.files("app").joinpath("ui_template.html")
    template_text = template_path.read_text(encoding="utf-8")
    replacements = {
        "__SNAPSHOTS_JSON__": json.dumps(snapshots, ensure_ascii=False),
        "__HAS_DATA__": "true" if snapshots else "false",
    }
    for placeholder, value in replacements.items():
        template_text = template_text.replace(placeholder, value)
    return template_text
