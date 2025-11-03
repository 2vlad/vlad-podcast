# 🚂 Railway Deployment Guide

## ✅ Railway Project Created

**Project:** vlad-podcast  
**URL:** https://vlad-podcast-production.up.railway.app  
**Dashboard:** https://railway.com/project/d1406937-9c1d-4d28-a020-958d80386379

---

## 🔧 Configuration Files Created

### `railway.json`
- Build configuration
- Deploy settings (1 replica, restart on failure)

### `nixpacks.toml`
- Python 3.9 runtime
- ffmpeg for audio processing
- Gunicorn production server

### `Procfile`
- Web process: `gunicorn --bind 0.0.0.0:$PORT web:app`

---

## ⚙️ Environment Variables Set

```bash
SITE_URL=https://2vlad.github.io/vlad-podcast
MEDIA_BASE_URL=https://2vlad.github.io/vlad-podcast/media
AUDIO_FORMAT=m4a
AUDIO_QUALITY=best
FEED_MAX_ITEMS=50
PODCAST_TITLE=Влад Слушает
PODCAST_DESCRIPTION=Запаиси для прогулок
PODCAST_AUTHOR=Влад
PODCAST_LANGUAGE=ru
PODCAST_CATEGORY=Leisure
AUTO_PUBLISH=github
GITHUB_REPO=2vlad/vlad-podcast
GITHUB_BRANCH=main
```

---

## 🚀 Deployment Status

Deployment is in progress. Check logs at:
https://railway.com/project/d1406937-9c1d-4d28-a020-958d80386379/service/0929106c-3e42-4cb5-869c-0989719d9ea2

---

## 📝 Next Steps

1. **Check deployment logs** in Railway dashboard
2. **Verify the app is running** at https://vlad-podcast-production.up.railway.app
3. **Test adding an episode** through the web interface
4. **Confirm auto-publish to GitHub** works from Railway

---

## 🔍 Troubleshooting

### If deployment fails:

1. Check build logs in Railway dashboard
2. Verify all environment variables are set
3. Check that `requirements.txt` includes all dependencies
4. Ensure `gunicorn` is in requirements
5. Verify `nixpacks.toml` has correct Python version

### Common issues:

- **Port binding**: Railway sets `$PORT` automatically
- **GitHub auth**: May need to set up GitHub credentials for auto-publish
- **ffmpeg**: Should be installed via nixpacks.toml

---

## 🛠️ Manual Commands

```bash
# Check status
cd /Users/admin/Dev/youtube-podcast
railway status

# View logs (streams in real-time)
railway logs

# List variables
railway variables

# Set a variable
railway variables --set "KEY=value"

# Redeploy
railway up
```

---

## 🌐 Access URLs

- **Web Interface:** https://vlad-podcast-production.up.railway.app
- **API Config:** https://vlad-podcast-production.up.railway.app/api/config
- **RSS Feed:** https://2vlad.github.io/vlad-podcast/rss.xml (GitHub Pages)

---

## 🎯 How It Works

1. **User accesses Railway URL** → Opens web interface
2. **Adds YouTube URL** → Downloads audio with yt-dlp
3. **Updates RSS feed** → Saves to `podcast/rss.xml`
4. **Auto-publishes to GitHub** → Copies to `docs/` and pushes
5. **GitHub Actions deploys** → Updates GitHub Pages
6. **RSS feed available** → Podcast apps can subscribe

---

## 📊 Architecture

```
Railway (Web Interface)
    ↓
yt-dlp (Download audio)
    ↓
Generate RSS Feed
    ↓
GitHub Publisher (Push to GitHub)
    ↓
GitHub Actions
    ↓
GitHub Pages (Public RSS Feed)
    ↓
Podcast Apps
```

---

**Note:** Railway hosts the web interface, but the actual RSS feed and media files are served from GitHub Pages to keep costs down and ensure reliability.
