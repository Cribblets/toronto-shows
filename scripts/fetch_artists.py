"""Refresh each site's artists.json from its Spotify playlists.

Uses the anonymous token from the public embed page plus the web player's
GraphQL endpoint. Both are unofficial, so on any failure we keep the existing
artists.json rather than failing the whole update.
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

FETCH_PLAYLIST_HASH = "19ff1327c29e99c208c86d7a9d8f1929cfdf3d3202a0ff4253c821f1901aa94d"
DATA = Path(__file__).resolve().parent.parent / "data"
SITES = {
    DATA / "artists.json": ["0xHA2e6A8i3uZiwBpTwujr"],  # I Like It Hard
    DATA / "electronic" / "artists.json": [
        "2HeWTWW4g3JXfXxg2xi2Q6",  # Deep into the Night
        "3UHSFab5U05ksYkNqlNZ0s",  # Haus
        "0tJsHMmIgKNxCbZavBddKA",  # Funkadelic Disco
    ],
}
UA = {"User-Agent": "Mozilla/5.0"}


def get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=30).read().decode()


def fetch(playlist_id, counts):
    html = get(f"https://open.spotify.com/embed/playlist/{playlist_id}", UA)
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    token = json.loads(m.group(1))["props"]["pageProps"]["state"]["settings"]["session"]["accessToken"]
    headers = {**UA, "Authorization": f"Bearer {token}", "app-platform": "WebPlayer"}

    offset, total = 0, None
    while total is None or offset < total:
        params = urllib.parse.urlencode({
            "operationName": "fetchPlaylist",
            "variables": json.dumps({"uri": f"spotify:playlist:{playlist_id}", "offset": offset, "limit": 100}),
            "extensions": json.dumps({"persistedQuery": {"version": 1, "sha256Hash": FETCH_PLAYLIST_HASH}}),
        })
        data = json.loads(get(f"https://api-partner.spotify.com/pathfinder/v1/query?{params}", headers))
        content = data["data"]["playlistV2"]["content"]
        total = content["totalCount"]
        for item in content["items"]:
            track = (item.get("itemV2") or {}).get("data") or {}
            for artist in (track.get("artists") or {}).get("items", []):
                name = artist["profile"]["name"]
                counts[name] = counts.get(name, 0) + 1
        offset += 100
    return total


def main():
    for out, playlists in SITES.items():
        counts, total = {}, 0
        try:
            for playlist_id in playlists:
                total += fetch(playlist_id, counts)
        except Exception as e:  # noqa: BLE001 - any failure falls back to the cached list
            print(f"Spotify fetch failed, keeping existing {out.name}: {e}", file=sys.stderr)
            continue
        if not counts:
            print(f"Spotify returned no artists, keeping existing {out.name}", file=sys.stderr)
            continue
        artists = [{"name": n, "tracks": c} for n, c in sorted(counts.items(), key=lambda x: (-x[1], x[0].lower()))]
        out.write_text(json.dumps(artists, indent=1, ensure_ascii=False) + "\n")
        print(f"{out.relative_to(DATA.parent)}: {total} tracks, {len(artists)} artists")


if __name__ == "__main__":
    main()
