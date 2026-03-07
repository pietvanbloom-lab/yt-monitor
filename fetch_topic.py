#!/usr/bin/env python3
"""
YouTube Topic Search — Trending Videos
Usage: python3 fetch_topic.py "Iran Krieg"
       python3 fetch_topic.py "Automobilsport"
Outputs: data/topic.json  (Heute / Monat / All)
"""
import os, sys, json, re, requests
from datetime import datetime, timezone, timedelta

YOUTUBE_API_KEY = None
OUT_PATH = os.path.join(os.path.dirname(__file__), "data", "topic.json")
MAX_RESULTS = 15  # per time slice

# ─── Load API key ────────────────────────────────────────────────
def load_api_key():
    env_path = os.path.expanduser("~/Documents/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("YOUTUBE_API_KEY"):
                    return line.split("=", 1)[1].strip()
    return os.environ.get("YOUTUBE_API_KEY")

# ─── Helpers ─────────────────────────────────────────────────────
def fetch(url, params):
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def parse_dur(iso):
    if not iso:
        return 0
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso)
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s

def fmt_dur(secs):
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def fmt_num(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)

# ─── YouTube search ──────────────────────────────────────────────
def search_videos(query, published_after=None):
    """Search YouTube for query, optionally filtered by date. Returns list of video IDs + basic info."""
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "viewCount",
        "maxResults": MAX_RESULTS,
        "key": YOUTUBE_API_KEY,
        "relevanceLanguage": "de",
        "safeSearch": "none",
    }
    if published_after:
        params["publishedAfter"] = published_after

    data = fetch("https://www.googleapis.com/youtube/v3/search", params)
    videos = []
    for item in data.get("items", []):
        snip = item.get("snippet", {})
        vid_id = item.get("id", {}).get("videoId", "")
        if not vid_id:
            continue
        thumb = (
            snip.get("thumbnails", {}).get("medium") or
            snip.get("thumbnails", {}).get("default") or {}
        ).get("url", "")
        videos.append({
            "id": vid_id,
            "title": snip.get("title", ""),
            "channel": snip.get("channelTitle", ""),
            "published_at": snip.get("publishedAt", ""),
            "thumbnail": thumb,
        })
    return videos

def enrich_with_stats(videos):
    """Add views, likes, duration to videos. Filters out Shorts (≤62s)."""
    if not videos:
        return []
    ids = [v["id"] for v in videos]
    data = fetch("https://www.googleapis.com/youtube/v3/videos", {
        "part": "statistics,contentDetails",
        "id": ",".join(ids),
        "key": YOUTUBE_API_KEY,
    })
    stats_map = {}
    for item in data.get("items", []):
        s = item.get("statistics", {})
        dur = parse_dur(item.get("contentDetails", {}).get("duration", "PT0S"))
        stats_map[item["id"]] = {
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
            "duration_seconds": dur,
        }

    now = datetime.now(timezone.utc)
    enriched = []
    for v in videos:
        s = stats_map.get(v["id"])
        if not s:
            continue
        dur = s["duration_seconds"]
        if 0 < dur <= 62:  # skip Shorts
            continue
        pub = v["published_at"]
        try:
            pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            days_since = max((now - pub_dt).total_seconds() / 86400, 0.1)
            pub_ts = int(pub_dt.timestamp())
        except Exception:
            days_since = 1
            pub_ts = 0

        views = s["views"]
        enriched.append({
            "id": v["id"],
            "title": v["title"],
            "channel": v["channel"],
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "thumbnail": v["thumbnail"],
            "published_at": pub,
            "published_at_ts": pub_ts,
            "duration_seconds": dur,
            "duration_formatted": fmt_dur(dur),
            "views": views,
            "likes": s["likes"],
            "views_formatted": fmt_num(views),
            "likes_formatted": fmt_num(s["likes"]),
            "views_per_day": round(views / days_since, 1),
        })

    # Sort by views descending
    enriched.sort(key=lambda v: v["views"], reverse=True)
    return enriched

# ─── Main ─────────────────────────────────────────────────────────
def main():
    global YOUTUBE_API_KEY

    if len(sys.argv) < 2:
        print("Usage: python3 fetch_topic.py \"Suchbegriff\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    YOUTUBE_API_KEY = load_api_key()
    if not YOUTUBE_API_KEY:
        print("❌ YOUTUBE_API_KEY nicht gefunden (~Documents/.env oder ENV)")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    heute_after  = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    monat_after  = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f'🔍 Suche nach: "{query}"')
    print("  → Heute…", flush=True)
    heute_raw  = search_videos(query, published_after=heute_after)
    print("  → Monat…", flush=True)
    monat_raw  = search_videos(query, published_after=monat_after)
    print("  → Gesamt…", flush=True)
    all_raw    = search_videos(query)

    print("  → Stats laden…", flush=True)
    heute_vids = enrich_with_stats(heute_raw)
    monat_vids = enrich_with_stats(monat_raw)
    all_vids   = enrich_with_stats(all_raw)

    print(f"  ✓ Heute: {len(heute_vids)} | Monat: {len(monat_vids)} | Gesamt: {len(all_vids)}")

    output = {
        "query": query,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sections": {
            "heute": heute_vids,
            "monat": monat_vids,
            "all":   all_vids,
        }
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Gespeichert: {OUT_PATH}")

if __name__ == "__main__":
    main()
