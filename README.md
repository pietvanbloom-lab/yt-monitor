# YouTube Monitor Dashboard

A static dashboard that fetches videos daily from curated YouTube channels, categorizes them using Claude Haiku, and displays them as a filterable web interface.

## Project Structure

```
.
├── fetch_data.py        # Data fetcher (YouTube API + Haiku)
├── index.html          # Dashboard (single-file, no build step)
├── data/
│   └── videos.json     # Auto-generated, committed to repo
└── .github/
    └── workflows/
        └── update.yml  # Daily GitHub Actions cron job
```

## Setup

### 1. Create GitHub Repository

```bash
git init yt-monitor
cd yt-monitor
# Copy files: fetch_data.py, index.html, README.md
mkdir -p data .github/workflows
cp update.yml .github/workflows/update.yml
echo '{"videos":[],"categories":[],"generated_at":"","total_videos":0,"total_channels":0}' > data/videos.json
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR_USERNAME/yt-monitor.git
git push -u origin main
```

### 2. Add API Keys as GitHub Secrets

Go to GitHub → Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|---|---|
| `YOUTUBE_API_KEY` | YouTube Data API v3 key (from Google Cloud Console) |
| `ANTHROPIC_API_KEY` | Anthropic API key |

### 3. Enable GitHub Pages (for Hosting)

GitHub → Repo → **Settings → Pages** → Source: **Deploy from a branch** → `main` / `/ (root)` → Save

The dashboard will then be available at: `https://YOUR_USERNAME.github.io/yt-monitor/`

#### Alternative: Vercel / Netlify

Simply connect the repository – both platforms automatically detect `index.html` as a static site. Free of charge.

## API Key Configuration (config.js)

To keep sensitive credentials out of the source code, reference your API keys via a separate config file.

Create a `config.example.js` as a template (safe to commit):

```js
// config.example.js – copy this file to config.js and fill in your values
// NEVER commit config.js to the repository!
const CONFIG = {
  YOUTUBE_API_KEY: "YOUR_YOUTUBE_API_KEY_HERE",
  CHANNEL_IDS: [
    "UCxxxxxxxxxxxxxxxxxxxxxx",  // Channel 1
    "UCyyyyyyyyyyyyyyyyyyyyyy"   // Channel 2
  ]
};
```

Add `config.js` to your `.gitignore`:

```bash
echo "config.js" >> .gitignore
```

In `index.html` or your JS files, load the config before using it:

```html
<script src="config.js"></script>
<script src="assets/js/dashboard.js"></script>
```

> **Note:** For production use on GitHub Pages, API keys placed in frontend JS are visible to anyone visiting the page. Use the GitHub Actions + static JSON pattern (described below) to avoid exposing keys in the browser.

### Recommended pattern: Static JSON via GitHub Actions

Instead of calling the YouTube API from the browser:

1. GitHub Actions runs `fetch_data.py` daily using secrets stored server-side.
2. The script writes results to `data/videos.json` and commits the file.
3. `index.html` fetches only the static JSON – no API key is ever exposed in the frontend.

This keeps the dashboard secure, fast, and within API quota limits.

## Local Development

```bash
# Install dependencies
pip install requests anthropic

# Run data fetch manually
YOUTUBE_API_KEY=xxx ANTHROPIC_API_KEY=xxx python fetch_data.py

# Start local server (to avoid CORS issues)
python -m http.server 8080
# → http://localhost:8080
```

## Cron Schedule

The GitHub Actions workflow runs daily at **07:00 UTC** (= 08:00 CET / 09:00 CEST).
It can also be triggered manually: Repo → **Actions → Update YouTube Data → Run workflow**

## Cost Overview

| Service | Cost |
|---|---|
| YouTube Data API | Free (10,000 units/day, ~200 used) |
| Anthropic (Haiku 4.5) | ~$0.10–0.20 / month |
| GitHub Actions | Free (2,000 min/month on free tier) |
| GitHub Pages / Vercel | Free |
| **Total** | **< $0.25 / month** |

## Customize Channels

Edit the `channels` list in `fetch_data.py`. Use the handle format: `@ChannelName` from the YouTube URL.
For channels without a handle: set `None` as handle and hardcode the `channel_id` directly in `get_channel_id()`.

## Upcoming Improvements

Planned features and enhancements for future development:

- [ ] **Multi-language support** – Translate the dashboard UI into English (currently German)
- [ ] **Per-video detail view** – Click a video card to see extended metadata and AI summary
- [ ] **Time-series charts** – Track video performance (views, likes) over time
- [ ] **Multiple channel groups / playlists** – Group channels by topic or category
- [ ] **Alert rules** – Highlight videos with unusually high growth or engagement
- [ ] **Dark / light theme toggle** – User-selectable color scheme
- [ ] **Export to CSV / JSON** – Allow users to download filtered video lists
- [ ] **`config.js` loader** – Move channel list and API key references into a dedicated config file for easier setup
- [ ] **Improved mobile layout** – Responsive design optimizations for small screens
- [ ] **README fully in English** – Migrate all inline comments and setup instructions to English

## Live Dashboard

https://pietvanbloom-lab.github.io/yt-monitor/

## License

This project is currently for personal use and experimentation.
Add a license (e.g. MIT) if you plan to share or open-source it.
