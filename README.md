# Toronto Heavy Shows

Upcoming Toronto-area concerts from bands on the Spotify playlist
[I Like It Hard](https://open.spotify.com/playlist/0xHA2e6A8i3uZiwBpTwujr).

## How it updates

- **Mondays 10:00 UTC**, the GitHub Action (`.github/workflows/update.yml`):
  1. `scripts/fetch_artists.py` refreshes `data/artists.json` from the playlist. If Spotify fails, it keeps the old list.
  2. `scripts/fetch_ticketmaster.py` pulls every music event within 60 km of Toronto for the next 18 months and keeps the ones whose lineup includes a playlist artist. It writes the result to `data/shows.json`.
- **Mondays, later in the day**, a scheduled Claude routine checks indie venue calendars that Ticketmaster doesn't cover and writes what it finds to `data/claude_shows.json`.

The page merges both files in the browser. When both sources list the same artist on the same date, it shows the Ticketmaster entry.

## `data/claude_shows.json` format

```json
[
  {
    "id": "claude-<artist-slug>-<yyyy-mm-dd>",
    "title": "Event name as listed",
    "artists": ["Exact name from artists.json"],
    "date": "2026-11-14",
    "time": "19:00:00",
    "venue": "Lee's Palace",
    "city": "Toronto",
    "url": "https://link-to-tickets-or-listing",
    "source": "claude",
    "found": "2026-10-05"
  }
]
```

## Setup

```sh
gh secret set TM_API_KEY          # paste your Ticketmaster Discovery API key
gh workflow run "Weekly show update"
```
