"""Save plain-text snapshots of venue and promoter event pages.

The Claude routines that look for non-Ticketmaster shows run in a sandbox that
can't reach most venue sites, so the GitHub Action downloads the pages instead
and the routines read the snapshots from data/<site>/pages/.
"""
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/128 Safari/537.36"}
PAGES = {
    DATA / "pages": {
        "lees-palace": "https://www.leespalace.com/",
        "horseshoe-tavern": "https://www.horseshoetavern.com/",
        "garrison": "https://www.garrisontoronto.com/",
        "hard-luck": "https://www.hardluckbar.com/",
        "bovine-sex-club": "https://www.bovinesexclub.com/",
        "collective-concerts": "https://www.collectiveconcerts.com/",
        "toronto-music-listings": "https://torontomusiclistings.com/",
    },
    DATA / "electronic" / "pages": {
        "coda": "https://codatoronto.com/events",
        "wiggle-room": "https://wiggleroomtoronto.com/wp-json/tribe/events/v1/events?per_page=100",
        "rebel": "https://www.rebeltoronto.com/",
        "toybox": "https://www.toyboxtoronto.com/",
        "dprtmnt": "https://www.dprtmnt.com/",
        "embrace-presents": "https://www.embracepresents.com/",
        "dice-toronto": "https://dice.fm/browse/toronto",
        "toronto-music-listings": "https://torontomusiclistings.com/",
    },
}


def to_text(raw):
    raw = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|tr|article|section)>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    lines = (re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def tribe_events_to_text(raw):
    """The Events Calendar (WordPress) JSON feed: one block per event, with the full description."""
    blocks = []
    for ev in json.loads(raw).get("events", []):
        venue = ev.get("venue") or {}
        blocks.append("\n".join([
            f"{ev['start_date']} - {html.unescape(ev['title'])}",
            f"Venue: {venue.get('venue', '')}",
            f"URL: {ev.get('url', '')}",
            to_text(ev.get("description", "")),
        ]))
    return "\n\n---\n\n".join(blocks)


def main():
    for out_dir, pages in PAGES.items():
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, url in pages.items():
            try:
                req = urllib.request.Request(url, headers=UA)
                raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
                text = tribe_events_to_text(raw) if "/wp-json/tribe/" in url else to_text(raw)
            except Exception as e:  # noqa: BLE001 - one broken venue site shouldn't stop the rest
                print(f"{name}: failed ({e})", file=sys.stderr)
                continue
            (out_dir / f"{name}.txt").write_text(f"Source: {url}\n\n{text}\n")
            print(f"{out_dir.relative_to(DATA.parent)}/{name}.txt: {len(text)} chars")
