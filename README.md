# Toronto Heavy Shows + Toronto Electronic Shows

Two pages listing upcoming Toronto-area concerts by artists from Spotify playlists:

| Page | Playlists | Data |
|---|---|---|
| `/` (heavy) | [I Like It Hard](https://open.spotify.com/playlist/0xHA2e6A8i3uZiwBpTwujr) | `data/` |
| `/electronic/` | [Deep into the Night](https://open.spotify.com/playlist/2HeWTWW4g3JXfXxg2xi2Q6), [Haus](https://open.spotify.com/playlist/3UHSFab5U05ksYkNqlNZ0s), [Funkadelic Disco](https://open.spotify.com/playlist/0tJsHMmIgKNxCbZavBddKA) | `data/electronic/` |

Playlists for each page are set in `SITES` in `scripts/fetch_artists.py`.

## How it updates

- **Mondays 10:00 UTC**, the GitHub Action (`.github/workflows/update.yml`):
  1. `scripts/fetch_artists.py` refreshes each page's `artists.json` from its playlists. If Spotify fails, it keeps the old list.
  2. `scripts/fetch_ticketmaster.py` pulls every music event within 60 km of Toronto for the next 18 months and, for each page, keeps the ones whose lineup includes one of its artists. It writes the result to that page's `shows.json`.
- **Mondays, later in the day**, a scheduled Claude routine for each page checks venue and promoter listings that Ticketmaster doesn't cover and writes what it finds to that page's `claude_shows.json`.

The page merges both files in the browser. When both sources list the same artist on the same date, it shows the Ticketmaster entry.

## `claude_shows.json` format (both pages)

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
