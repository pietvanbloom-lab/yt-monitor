# YouTube Monitor Dashboard

Statisches Dashboard das täglich Videos aus kuratierten YouTube-Kanälen fetcht, mit Claude Haiku kategorisiert und als filterbares Web-Interface darstellt.

## Aufbau

```
.
├── fetch_data.py          # Daten-Fetcher (YouTube API + Haiku)
├── index.html             # Dashboard (Single-File, kein Build-Schritt)
├── data/
│   └── videos.json        # Auto-generiert, wird committed
└── .github/
    └── workflows/
        └── update.yml     # Täglicher GitHub Actions Cron
```

## Setup

### 1. GitHub Repository erstellen

```bash
git init yt-monitor
cd yt-monitor
# Dateien reinkopieren: fetch_data.py, index.html, README.md
mkdir -p data .github/workflows
cp update.yml .github/workflows/update.yml
echo '{"videos":[],"categories":[],"generated_at":"","total_videos":0,"total_channels":0}' > data/videos.json
git add .
git commit -m "init"
git remote add origin https://github.com/DEIN_USERNAME/yt-monitor.git
git push -u origin main
```

### 2. API Keys als GitHub Secrets hinterlegen

In GitHub → Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Wert |
|---|---|
| `YOUTUBE_API_KEY` | YouTube Data API v3 Key (aus Google Cloud Console) |
| `ANTHROPIC_API_KEY` | Anthropic API Key |

### 3. GitHub Pages aktivieren (für Hosting)

GitHub → Repo → **Settings → Pages**
→ Source: **Deploy from a branch** → `main` / `/ (root)` → Save

Das Dashboard ist dann erreichbar unter:
`https://DEIN_USERNAME.github.io/yt-monitor/`

### Alternative: Vercel/Netlify

Einfach das Repo verbinden – beide Plattformen erkennen `index.html` automatisch als Static Site. Kostenlos.

---

## Lokaler Test

```bash
# Dependencies installieren
pip install requests anthropic

# Einmalig manuell fetchen
YOUTUBE_API_KEY=xxx ANTHROPIC_API_KEY=xxx python fetch_data.py

# Lokalen Server starten (um CORS zu vermeiden)
python -m http.server 8080
# → http://localhost:8080
```

---

## Cron-Zeitplan

Der GitHub Actions Workflow läuft täglich um **07:00 UTC** (= 08:00 MEZ / 09:00 MESZ).
Manuell auslösbar unter: Repo → **Actions → Update YouTube Data → Run workflow**

---

## Kosten

| Dienst | Kosten |
|---|---|
| YouTube Data API | Kostenlos (10.000 Units/Tag, ~200 genutzt) |
| Anthropic (Haiku 4.5) | ~$0.10–0.20 / Monat |
| GitHub Actions | Kostenlos (2.000 Min/Monat free tier) |
| GitHub Pages / Vercel | Kostenlos |
| **Gesamt** | **< $0.25 / Monat** |

---

## Kanäle anpassen

In `fetch_data.py` die `channels`-Liste bearbeiten. Handle-Format: `@KanalName` aus der YouTube-URL.
Für Kanäle ohne Handle: `None` als Handle + `channel_id` direkt in `get_channel_id()` hardcoden.
