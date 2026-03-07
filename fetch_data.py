#!/usr/bin/env python3
"""
YouTube Monitoring Dashboard - Data Fetcher
Fetches 30 days of videos from curated channels, categorizes via Haiku, outputs JSON.
"""
import os, sys, json, re, requests
from datetime import datetime, timezone, timedelta
from anthropic import Anthropic

YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
OUT_PATH = os.path.join(os.path.dirname(__file__), "data", "videos.json")
DAYS_BACK = 30

channels = [
    ('Weichreite TV', '@Weichreite'),
    ('eingollan', '@eingollan'),
    ('Julian Ivanov | KI-Automatisierung', '@Julian-Ivanov'),
    ('DER SPIEGEL', '@derspiegel'),
    ('AfD-Fraktion Bundestag', '@AfDFraktionimBundestag'),
    ('VinceandWeed', '@VinceAndWeed'),
    ('Serge Menga - Klartext + Aktiv !', '@SergeMengaNsibu1977'),
    ('Bonorum - Premium Hemp Products', '@Bonorum_Official'),
    ('WELT Nachrichtensender', '@WELTVideoTV'),
    ('TNT Sports', '@tntsports'),
    ('ARTE Concert', '@arteconcert'),
    ('Sen', '@Sen'),
    ('Growmotion', '@growmotion.official'),
    ('backyard mix', '@thebackyardmix'),
    ('MoBuds314', '@MoBuds314'),
    ('Red Bull Motorsports', '@RedBullMotorsports'),
    ('Boiler Room', '@boilerroom'),
    ('VICE', '@VICE'),
    ('Nugsmasher', '@Nugsmasher'),
    ('Vericut', '@CgtechVERICUT'),
    ('Sanding Shit', '@sandingshit'),
    ('Hydra Unlimited', '@HydraUnlimited'),
    ('Athena Ag', '@athenacultivation'),
    ('GARDEN SUPPLY GUYS', '@gardensupplyguys'),
    ('sens cuisine', '@senscuisine'),
    ('Richie Hawtin', '@richiehawtin'),
    ('Robotman - Topic', None),  # special: channel ID known
]
ROBOTMAN_ID = "UCkR_n01skKEaRnBXdldzawQ"

CATEGORIES = [
    "Politik & Gesellschaft",
    "Sport & Motorsport",
    "Musik & Festival",
    "Cannabis & Anbau",
    "Technik & KI",
    "Food & Lifestyle",
    "News & Nachrichten",
    "Sonstiges",
]

def fetch(url, params):
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def parse_dur(iso):
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso)
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s

def fmt_dur(secs):
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def fmt_num(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)

def get_channel_id(handle):
    data = fetch("https://www.googleapis.com/youtube/v3/channels", {
        "part": "id",
        "forHandle": handle.lstrip("@"),
        "key": YOUTUBE_API_KEY,
    })
    items = data.get("items", [])
    return items[0]["id"] if items else None

def get_playlist_videos(playlist_id, since_iso):
    videos = []
    page_token = None
    while True:
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
            "key": YOUTUBE_API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token
        data = fetch("https://www.googleapis.com/youtube/v3/playlistItems", params)
        for item in data.get("items", []):
            snip = item["snippet"]
            pub = snip.get("publishedAt", "")
            if pub < since_iso:
                return videos  # sorted descending, stop early
            vid_id = snip.get("resourceId", {}).get("videoId")
            if vid_id:
                videos.append({
                    "id": vid_id,
                    "title": snip.get("title", ""),
                    "published_at": pub,
                    "thumbnail": (snip.get("thumbnails", {}).get("medium") or
                                  snip.get("thumbnails", {}).get("default") or {}).get("url", ""),
                })
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return videos

def get_video_stats(video_ids):
    """Batch fetch stats + duration for up to 50 videos."""
    stats = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        data = fetch("https://www.googleapis.com/youtube/v3/videos", {
            "part": "statistics,contentDetails",
            "id": ",".join(batch),
            "key": YOUTUBE_API_KEY,
        })
        for item in data.get("items", []):
            vid_id = item["id"]
            s = item.get("statistics", {})
            dur = parse_dur(item.get("contentDetails", {}).get("duration", "PT0S"))
            stats[vid_id] = {
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "duration_seconds": dur,
            }
    return stats

def categorize_videos(titles):
    """Batch-categorize video titles via Claude Haiku 4.5 (200 per call)."""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    cats_str = ", ".join(CATEGORIES)
    results = []
    BATCH = 200

    for i in range(0, len(titles), BATCH):
        batch_titles = titles[i:i+BATCH]
        numbered = "\n".join(f"{j+1}. {t}" for j, t in enumerate(batch_titles))
        prompt = (
            f"Categorize each video title into exactly one category from this list: {cats_str}\n\n"
            f"Titles:\n{numbered}\n\n"
            f"Reply with ONLY a JSON array of strings, one category per title, in order. "
            f'Example: ["Politik & Gesellschaft", "Musik & Festival", ...]'
        )
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = msg.content[0].text.strip()
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                batch_result = json.loads(match.group())
                if len(batch_result) == len(batch_titles):
                    results.extend(batch_result)
                    print(f"  Batch {i//BATCH + 1}/{-(-len(titles)//BATCH)} kategorisiert", flush=True)
                    continue
        except Exception as e:
            print(f"  Kategorisierung Batch {i//BATCH + 1} Fehler: {e}")
        # Fallback fuer diesen Batch
        results.extend(["Sonstiges"] * len(batch_titles))

    return results

def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=DAYS_BACK)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    all_videos = []
    processed_channels = 0

    for name, handle in channels:
        try:
            if handle is None:
                channel_id = ROBOTMAN_ID
            else:
                print(f"  Resolving {handle}...", flush=True)
                channel_id = get_channel_id(handle)
                if not channel_id:
                    print(f"  Could not resolve {handle}, skipping")
                    continue

            playlist_id = "UU" + channel_id[2:]
            print(f"  Fetching {name}...", flush=True)
            vids = get_playlist_videos(playlist_id, since_iso)

            for v in vids:
                v["channel"] = name
                v["channel_handle"] = handle or "@Robotman"

            all_videos.extend(vids)
            processed_channels += 1
        except Exception as e:
            print(f"  {name}: {e}")

    print(f"\nFetched {len(all_videos)} raw videos from {processed_channels} channels")

    # Batch fetch stats
    print("Fetching video stats...", flush=True)
    video_ids = [v["id"] for v in all_videos]
    stats = get_video_stats(video_ids)

    # Merge stats + filter Shorts
    enriched = []
    for v in all_videos:
        s = stats.get(v["id"])
        if not s:
            continue
        dur = s["duration_seconds"]
        if dur <= 62:  # filter Shorts
            continue
        pub_dt = datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
        days_since = max((now - pub_dt).total_seconds() / 86400, 0.1)
        views = s["views"]
        enriched.append({
            "id": v["id"],
            "title": v["title"],
            "channel": v["channel"],
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "thumbnail": v["thumbnail"],
            "published_at": v["published_at"],
            "published_at_ts": int(pub_dt.timestamp()),
            "duration_seconds": dur,
            "duration_formatted": fmt_dur(dur),
            "views": views,
            "likes": s["likes"],
            "views_formatted": fmt_num(views),
            "likes_formatted": fmt_num(s["likes"]),
            "views_per_day": round(views / days_since, 1),
            "category": None,  # filled below
        })

    print(f"After Shorts filter: {len(enriched)} videos")

    # Categorize via Haiku
    if enriched:
        print("Categorizing via Claude Haiku...", flush=True)
        titles = [v["title"] for v in enriched]
        cats = categorize_videos(titles)
        for v, cat in zip(enriched, cats):
            v["category"] = cat

    # Build output
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    output = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "days_back": DAYS_BACK,
        "total_videos": len(enriched),
        "total_channels": processed_channels,
        "categories": CATEGORIES,
        "videos": enriched,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(enriched)} videos to {OUT_PATH}")

if __name__ == "__main__":
    main()
