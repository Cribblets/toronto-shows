"""Pull every Toronto-area music event from Ticketmaster once, then for each
site keep the ones featuring an artist from its artists.json and write its
shows.json.

Needs TM_API_KEY (free key from developer.ticketmaster.com).
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
API = "https://app.ticketmaster.com/discovery/v2/events.json"
TORONTO = "43.6532,-79.3832"
RADIUS_KM = 60  # covers the GTA incl. Oshawa, Hamilton-ish, Vaughan
MONTHS_AHEAD = 18
PAGE_SIZE = 200
MAX_DEEP = 1000  # Discovery API refuses size*page beyond this
SITES = [DATA, DATA / "electronic"]


def norm(s):
    s = re.sub(r"\s*\(\d+\)$", "", s)  # Spotify disambiguation: "Love and Death (2)"
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"^the ", "", s)


def get(params):
    url = f"{API}?{urllib.parse.urlencode(params)}"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise
        finally:
            time.sleep(0.25)  # stay under 5 req/s


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def events_between(key, start, end):
    base = {
        "apikey": key, "latlong": TORONTO, "radius": RADIUS_KM, "unit": "km",
        "classificationName": "music", "startDateTime": iso(start), "endDateTime": iso(end),
        "size": PAGE_SIZE, "sort": "date,asc",
    }
    first = get({**base, "page": 0})
    total = first.get("page", {}).get("totalElements", 0)
    if total > MAX_DEEP and end - start > timedelta(days=2):
        mid = start + (end - start) / 2
        return events_between(key, start, mid) + events_between(key, mid, end)
    events = first.get("_embedded", {}).get("events", [])
    pages = min(first.get("page", {}).get("totalPages", 1), MAX_DEEP // PAGE_SIZE)
    for p in range(1, pages):
        events += get({**base, "page": p}).get("_embedded", {}).get("events", [])
    return events


def match(site, events):
    artists = json.loads((site / "artists.json").read_text())
    by_norm = {norm(a["name"]): a for a in artists}
    # Event-title matching is only safe for multi-word names; "Seven" or "Red" would match everything.
    title_matchable = {n: a for n, a in by_norm.items() if len(n.split()) >= 2}

    shows = []
    for ev in events:
        emb = ev.get("_embedded", {})
        lineup = [a["name"] for a in emb.get("attractions", [])]
        matched = {by_norm[norm(n)]["name"] for n in lineup if norm(n) in by_norm}
        title = f" {norm(ev['name'])} "
        matched |= {a["name"] for n, a in title_matchable.items() if f" {n} " in title}
        if not matched:
            continue
        venue = (emb.get("venues") or [{}])[0]
        dates = ev.get("dates", {})
        shows.append({
            "id": f"tm-{ev['id']}",
            "title": ev["name"],
            "artists": sorted(matched),
            "lineup": lineup,
            "date": dates.get("start", {}).get("localDate"),
            "time": dates.get("start", {}).get("localTime"),
            "status": dates.get("status", {}).get("code"),
            "venue": venue.get("name"),
            "city": (venue.get("city") or {}).get("name"),
            "url": ev.get("url"),
            "source": "ticketmaster",
        })

    shows.sort(key=lambda s: (s["date"] or "", s["time"] or ""))
    (site / "shows.json").write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artist_count": len(artists),
        "shows": shows,
    }, indent=1, ensure_ascii=False) + "\n")
    print(f"{site.relative_to(DATA.parent)}: {len(shows)} shows matched")


def main():
    key = os.environ.get("TM_API_KEY")
    if not key:
        sys.exit("TM_API_KEY is not set")

    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=30 * MONTHS_AHEAD)
    events = list({ev["id"]: ev for ev in events_between(key, start, end)}.values())
    print(f"{len(events)} Toronto-area music events from Ticketmaster")
    for site in SITES:
        match(site, events)


if __name__ == "__main__":
    main()
