# Railway Configuration Guide

## 🚀 Quick Setup on Railway

### Step 1: Add Environment Variables

Go to Railway Dashboard → `vlad-podcast` → Settings → Variables

Add these **required** variables:

```bash
SITE_URL=https://vlad-podcast-production.up.railway.app
MEDIA_BASE_URL=https://vlad-podcast-production.up.railway.app/media
```

**⚠️ IMPORTANT:** Replace `vlad-podcast-production.up.railway.app` with your actual Railway domain.

#### How to find your Railway URL:
1. Go to Railway Dashboard
2. Click on your `vlad-podcast` project
3. Go to "Settings" tab
4. Look for "Domains" section
5. Copy the `*.up.railway.app` domain

---

### Step 2: Add Optional Variables (Recommended)

```bash
# Podcast Metadata
PODCAST_TITLE=My YouTube Podcast
PODCAST_AUTHOR=Your Name
PODCAST_DESCRIPTION=My personal podcast feed from YouTube
PODCAST_LANGUAGE=en
PODCAST_CATEGORY=Technology

# Audio Settings
AUDIO_FORMAT=m4a
AUDIO_QUALITY=best

# Feed Settings
FEED_MAX_ITEMS=50

# Auto-Publish (if using GitHub Pages)
AUTO_PUBLISH=github
GITHUB_REPO=username/repo-name
GITHUB_BRANCH=main
```

---

### Step 3: Add Volume for Persistent Storage

**Why?** Without a volume, media files will be deleted on every deployment.

1. Railway Dashboard → Settings → Volumes
2. Click "New Volume"
3. Set Mount Path: `/app/podcast`
4. Click "Add"

This ensures your media files and RSS feed persist between deployments.

---

### Step 4: Deploy

Railway will automatically redeploy when you:
- Add/change environment variables
- Push new code to GitHub

---

## 🔍 Verify Configuration

### Option 1: Use the Configuration Checker (Recommended)

Run this command in Railway Shell:

```bash
python check_config.py
```

This will check:
- ✅ All required environment variables
- ✅ Directory structure
- ✅ File permissions
- ✅ URL configuration
- ✅ Python dependencies
- ✅ Configuration loading

**How to access Railway Shell:**
1. Railway Dashboard → Your Service
2. Click "..." menu (top right)
3. Click "Shell" or "Terminal"

---

### Option 2: Manual Verification

#### 1. Check Environment Variables

In Railway Shell:

```bash
echo $SITE_URL
echo $MEDIA_BASE_URL
```

Both should output your Railway URL.

#### 2. Check Web Interface

Open in browser:
```
https://your-app.up.railway.app/
```

Should show the web form.

#### 3. Check Episodes API

```
https://your-app.up.railway.app/episodes
```

Should return JSON with episodes list.

#### 4. Check RSS Feed

```
https://your-app.up.railway.app/rss.xml
```

Should return XML RSS feed.

---

## 🐛 Troubleshooting

### Problem: "Episodes not appearing in feed"

**Cause:** Missing or incorrect environment variables.

**Fix:**
1. Run configuration checker:
   ```bash
   python check_config.py
   ```

2. Add missing variables in Railway Dashboard → Variables

3. Wait for automatic redeploy

4. Re-add the episode (old episodes may have wrong URLs)

---

### Problem: "Media files not accessible"

**Cause:** No volume mounted or wrong MEDIA_BASE_URL.

**Fix:**
1. Add Volume at `/app/podcast` (see Step 3 above)

2. Verify MEDIA_BASE_URL:
   ```bash
   echo $MEDIA_BASE_URL
   ```
   Should be: `https://your-app.up.railway.app/media`

3. Run fix script to update existing episodes:
   ```bash
   python fix_media_urls.py
   ```

---

### Problem: "RSS feed shows old/wrong URLs"

**Cause:** Episodes were added before MEDIA_BASE_URL was configured.

**Fix:**
1. Make sure MEDIA_BASE_URL is set correctly

2. Run the URL fix script:
   ```bash
   python fix_media_urls.py
   ```

This will update all episode URLs in the RSS feed.

---

### Problem: "Configuration errors on startup"

**Cause:** Missing required environment variables.

**Fix:**
1. Check Railway logs:
   ```
   Railway Dashboard → Observability → Logs
   ```

2. Look for configuration errors

3. Add missing variables in Settings → Variables

4. Railway will auto-redeploy

---

## 📝 Complete Environment Variable Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SITE_URL` | Your Railway app URL | `https://vlad-podcast-production.up.railway.app` |
| `MEDIA_BASE_URL` | Base URL for media files | `https://vlad-podcast-production.up.railway.app/media` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PODCAST_TITLE` | Your podcast name | `YouTube to Podcast` |
| `PODCAST_AUTHOR` | Your name | `Your Name` |
| `PODCAST_DESCRIPTION` | Podcast description | `Personal podcast feed...` |
| `PODCAST_LANGUAGE` | Language code | `en` |
| `PODCAST_CATEGORY` | iTunes category | `Technology` |
| `AUDIO_FORMAT` | Audio format (m4a/mp3) | `m4a` |
| `AUDIO_QUALITY` | Audio quality | `best` |
| `FEED_MAX_ITEMS` | Max episodes in feed | `50` |
| `AUTO_PUBLISH` | Auto-publish mode | `manual` |
| `GITHUB_REPO` | GitHub repo for auto-publish | - |
| `GITHUB_BRANCH` | Git branch | `main` |

---

## 🎯 Post-Deployment Checklist

After configuring Railway, verify:

- [ ] Environment variables are set
- [ ] Volume is mounted at `/app/podcast`
- [ ] Web interface loads: `https://your-app.up.railway.app/`
- [ ] Configuration checker passes: `python check_config.py`
- [ ] Can add episode via web form
- [ ] Episodes appear at: `https://your-app.up.railway.app/episodes`
- [ ] RSS feed works: `https://your-app.up.railway.app/rss.xml`
- [ ] Media files are accessible

---

## 🔗 Useful Railway Commands

### View Logs
```bash
# In Railway Dashboard
Observability → Logs
```

### Access Shell
```bash
# In Railway Dashboard
Click "..." → Shell
```

### Restart Service
```bash
# In Railway Dashboard
Settings → Restart
```

### Force Redeploy
```bash
# Push an empty commit to trigger redeploy
git commit --allow-empty -m "Trigger redeploy"
git push
```

---

## 📚 Related Documentation

- [DEPLOYMENT_SUMMARY.md](./DEPLOYMENT_SUMMARY.md) - Complete deployment guide
- [RAILWAY_MEDIA_FIX.md](./RAILWAY_MEDIA_FIX.md) - Media serving setup
- [README.md](./README.md) - General project documentation

---

## 💡 Tips

### Tip 1: Use GitHub Pages + Railway Hybrid

- **Railway:** Web interface and download processing
- **GitHub Pages:** RSS feed and media hosting (free, unlimited bandwidth)

Set in Railway:
```bash
SITE_URL=https://username.github.io/repo-name
MEDIA_BASE_URL=https://username.github.io/repo-name/media
AUTO_PUBLISH=github
GITHUB_REPO=username/repo-name
```

### Tip 2: Monitor Railway Logs

Watch logs when adding episodes:
```
Railway → Observability → Logs → Enable Live Logs
```

This helps debug download/processing issues in real-time.

### Tip 3: Test Locally First

Before deploying to Railway, test locally:

```bash
# Create .env file
cp .env.example .env

# Edit .env with test values
SITE_URL=http://localhost:5001
MEDIA_BASE_URL=http://localhost:5001/media

# Run checker
python check_config.py

# Start server
python web.py
```

---

## 🆘 Need Help?

If you encounter issues:

1. Run configuration checker: `python check_config.py`
2. Check Railway logs for errors
3. Verify all environment variables are set
4. Make sure volume is mounted
5. Try re-adding an episode after fixing configuration

---

**Last Updated:** 2025-11-04
