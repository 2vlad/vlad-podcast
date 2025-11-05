# 📂 File Upload Feature

## Overview

You can now add podcast episodes by uploading audio/video files directly, in addition to YouTube URLs!

---

## Supported Formats

- **MP3** - Direct upload, ready to use
- **MP4** - Auto-converted to M4A audio
- **M4A** - Direct upload, ready to use

**Maximum file size:** 500MB

---

## How to Upload

### Method 1: Drag & Drop

1. Open https://vlad-podcast-production.up.railway.app/
2. Click the **"Upload File"** tab
3. Drag your MP3/MP4 file into the upload zone
4. Fill in title and description (optional)
5. Click **"Upload and Add"**

### Method 2: Browse

1. Click the **"Upload File"** tab
2. Click anywhere in the upload zone
3. Select your file from the file picker
4. Fill in metadata
5. Click **"Upload and Add"**

---

## Features

### Auto-Conversion
- MP4 files are automatically converted to M4A (audio only)
- Uses ffmpeg for high-quality conversion
- Original video is removed after conversion

### Metadata
- **Title:** Optional. If not provided, uses filename
- **Description:** Optional. Defaults to "Uploaded audio: [filename]"
- **Duration:** Extracted automatically (if available)

### Duplicate Detection
- Each file gets a unique ID based on its content (MD5 hash)
- Uploading the same file twice won't create duplicates

### RSS Integration
- Uploaded files appear in RSS feed immediately
- Same workflow as YouTube episodes
- All episodes preserved (not replaced)

---

## Technical Details

### File Processing

1. **Upload:** File saved to `podcast/temp/`
2. **Validation:** Check type, size
3. **Conversion** (if MP4):
   - Extract audio with ffmpeg
   - Save as M4A
   - Remove original MP4
4. **ID Generation:** MD5 hash (first 11 chars)
5. **RSS Update:** Add to feed
6. **Cleanup:** Remove temporary file

### Storage

- Files stored in: `/app/podcast/media/`
- Accessible via: `https://your-app.up.railway.app/media/[hash].m4a`
- Persisted in Railway Volume

### API Endpoint

```
POST /api/upload
Content-Type: multipart/form-data

Parameters:
- file: The audio/video file (required)
- title: Episode title (optional)
- description: Episode description (optional)

Response:
{
  "job_id": 123,
  "status": "pending",
  "filename": "myfile.mp3"
}
```

---

## Examples

### Example 1: Upload MP3 Podcast

```
File: my-podcast-episode.mp3 (45MB)
Title: "Episode 5: Deep Dive into AI"
Description: "Discussion about latest AI developments"

Result:
- Audio URL: .../media/a1b2c3d4e5f.mp3
- Title: "Episode 5: Deep Dive into AI"
- Description: "Discussion about latest AI developments"
- Duration: Auto-detected
```

### Example 2: Upload MP4 Video

```
File: interview.mp4 (200MB)
Title: (leave empty)
Description: (leave empty)

Result:
- Converted to: .../media/f6e7d8c9b0a.m4a
- Title: "interview" (from filename)
- Description: "Uploaded audio: interview.mp4"
- Duration: Auto-detected
```

---

## Troubleshooting

### "Invalid file type"
**Solution:** Only MP3, MP4, M4A are supported. Check file extension.

### "File too large"
**Solution:** Maximum 500MB. Compress your file or split it.

### "Upload failed"
**Possible causes:**
- Network timeout
- Disk full
- Invalid file

**Solution:**
- Try smaller file
- Check Railway logs
- Contact support

### "Episode not appearing"
**Solution:**
- Refresh page
- Check `/api/episodes` endpoint
- Verify file was processed (check logs)

---

## Comparison: YouTube vs Upload

| Feature | YouTube URL | File Upload |
|---------|-------------|-------------|
| Source | YouTube video | Local file |
| Max Size | Unlimited (YouTube) | 500MB |
| Formats | Any YouTube video | MP3, MP4, M4A |
| Metadata | Auto from YouTube | Manual or filename |
| Thumbnail | Auto from YouTube | None |
| Duration | Auto-detected | Auto-detected |
| Processing Time | 30s - 5min (depends on video length) | 10s - 2min (depends on file size) |

---

## Use Cases

### 1. Personal Recordings
Upload your own voice memos, interviews, or recordings

### 2. External Content
Add content from sources other than YouTube

### 3. Edited Audio
Upload pre-edited podcast episodes

### 4. Archived Content
Add old episodes that aren't on YouTube

### 5. Original Productions
Upload your original podcast episodes

---

## Limits

- **File Size:** 500MB per file
- **Upload Speed:** Depends on your connection
- **Storage:** Railway Volume (5GB total)
- **Processing:** One file at a time

---

## Tips

### Best Practices

1. **Use descriptive filenames** - They become default titles
2. **Compress large files** - Faster upload
3. **Use MP3 for smaller files** - No conversion needed
4. **Add metadata** - Better organization

### Optimization

- **MP3:** 128kbps for speech, 192-320kbps for music
- **M4A:** AAC codec, quality level 2-4
- **MP4:** Will be converted, so lower quality is fine

---

## Future Enhancements

Planned features:
- [ ] Extract duration from uploaded files
- [ ] Support for more formats (WAV, FLAC)
- [ ] Batch upload (multiple files)
- [ ] Custom thumbnails for uploaded episodes
- [ ] ID3 tag extraction
- [ ] Progress bar during upload

---

## Security

- ✅ File type validation
- ✅ Size limit enforcement
- ✅ Secure filename handling
- ✅ Hash-based IDs (no filename collisions)
- ✅ Temporary file cleanup

---

**Happy uploading!** 🎙️
