# Fixing Media URLs for Railway Deployment

## Problem
Media files were being downloaded but not accessible because:
1. No endpoints in web.py to serve media files
2. MEDIA_BASE_URL pointed to GitHub Releases (files not uploaded there)

## Solution
Now media files are served directly from Railway deployment:
- Added `/media/<filename>` endpoint to serve media files
- Added `/rss.xml` endpoint to serve RSS feed
- Media files stay on Railway server and are accessible via HTTPS

## Required Steps

### 1. Update Railway Environment Variables

Go to your Railway project → Variables tab and update:

```bash
# Change from GitHub Releases URL:
# MEDIA_BASE_URL="https://github.com/2vlad/vlad-podcast/releases/download/media-files"

# To Railway domain:
MEDIA_BASE_URL="https://vlad-podcast-production.up.railway.app/media"

# Also update SITE_URL to Railway:
SITE_URL="https://vlad-podcast-production.up.railway.app"
```

**Note:** Replace `vlad-podcast-production.up.railway.app` with your actual Railway domain.

### 2. Deploy New Code

The code has been updated with:
- Media serving endpoint: `/media/<filename>`
- RSS serving endpoint: `/rss.xml`

After updating environment variables, Railway will automatically redeploy.

### 3. Fix Existing RSS Feed (After Deployment)

After deployment completes, run this command in Railway console or via SSH:

```bash
python3 fix_media_urls.py
```

This will update all existing episode URLs in the RSS feed to point to the new Railway media URLs.

### 4. Test

#### Test RSS Feed
```bash
curl https://vlad-podcast-production.up.railway.app/rss.xml
```

Should return your RSS feed with episodes.

#### Test Media Files
```bash
curl -I https://vlad-podcast-production.up.railway.app/media/tZPTiAvvG0w.m4a
```

Should return `200 OK` and the audio file.

### 5. Update Podcast App

In your podcast app (Apple Podcasts, Overcast, etc.), update the feed URL to:

```
https://vlad-podcast-production.up.railway.app/rss.xml
```

## Architecture

### Before (Broken)
```
User adds video → Railway downloads → Updates RSS with GitHub Releases URLs
                                    → But files never uploaded to GitHub!
                                    → Episodes show in feed but audio doesn't play ❌
```

### After (Working)
```
User adds video → Railway downloads → Stores in /app/podcast/media/
                                   → Updates RSS with Railway URLs
                                   → Flask serves files via /media/<filename>
                                   → Episodes play correctly ✅
```

## File Persistence

⚠️ **Important:** Railway ephemeral storage means files are lost on redeploy!

**Solutions:**
1. **Railway Volume** (Recommended): Mount a persistent volume at `/app/podcast/media`
   - Go to Railway project → Settings → Volumes
   - Add volume: `/app/podcast/media`
   - Size: 10GB (adjust based on needs)

2. **External Storage**: Use S3, Cloudflare R2, or similar for permanent storage

## Benefits

✅ Simple deployment - files served from same domain
✅ No need for GitHub Releases or external hosting
✅ RSS and media on same server (CORS-friendly)
✅ Easy to debug and monitor

## Monitoring

Check logs to see media requests:
```bash
railway logs
```

You should see requests like:
```
GET /media/tZPTiAvvG0w.m4a - 200
GET /rss.xml - 200
```

## Troubleshooting

### Episodes not showing
- Check RSS feed has correct MEDIA_BASE_URL in `<enclosure>` tags
- Run `fix_media_urls.py` to update URLs

### Audio not playing
- Test media URL directly: `https://your-domain.up.railway.app/media/VIDEO_ID.m4a`
- Check Railway logs for 404 errors
- Verify files exist: `ls -lh /app/podcast/media/`

### Files disappearing after redeploy
- Set up Railway Volume for persistent storage
- Or use external storage (S3, R2)
