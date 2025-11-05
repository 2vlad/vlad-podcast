# 🎵 Automatic MP3 Conversion Guide

## Why MP3?

Your podcast now **automatically converts all audio to MP3** format for maximum compatibility, especially with:

- ✅ **Light Phone** - requires MP3 format
- ✅ **Minimal podcast players** - often MP3-only
- ✅ **Older devices** - universal support
- ✅ **All podcast apps** - MP3 is the most compatible format

## How It Works

### 1. **Automatic Conversion** (Default)

When you add a YouTube video or upload a file:

```
YouTube Video → Download (M4A) → Auto-Convert to MP3 → Add to RSS Feed
```

**Settings:**
- Quality: **VBR ~190kbps** (excellent quality, small size)
- Format: **audio/mpeg** (MP3)
- Conversion: **FFmpeg** (high quality)

### 2. **What Changed**

#### Before:
```xml
<enclosure url=".../video.m4a" 
           type="audio/mp4" />
```

#### After:
```xml
<enclosure url=".../video.mp3" 
           type="audio/mpeg" />
```

## Convert Existing Files

If you have existing M4A files, convert them:

```bash
# Convert all M4A files to MP3
python3 convert_existing_to_mp3.py

# Regenerate RSS feed with MP3 files
python3 regenerate_feed.py
```

This will:
1. ✅ Convert all `.m4a` files to `.mp3`
2. ✅ Remove original M4A files
3. ✅ Update RSS feed with MP3 URLs

## Manual Conversion

To manually convert a single file:

```bash
# Convert specific file
python3 -m utils.audio_converter input.m4a output.mp3

# With custom quality (0-9, 2 is recommended)
python3 -m utils.audio_converter input.m4a output.mp3 2
```

## Quality Levels

| Level | Bitrate | Quality | Use Case |
|-------|---------|---------|----------|
| 0 | ~245 kbps | Best | Audiophile |
| 2 | **~190 kbps** | **Excellent** | **Recommended** ✅ |
| 4 | ~165 kbps | Very Good | Smaller size |
| 6 | ~115 kbps | Good | Mobile |
| 9 | ~65 kbps | Acceptable | Voice only |

**Default: Level 2** (~190kbps VBR) - best balance of quality and size

## Technical Details

### FFmpeg Command Used:

```bash
ffmpeg -i input.m4a \
       -vn \
       -acodec libmp3lame \
       -q:a 2 \
       -ar 44100 \
       -ac 2 \
       output.mp3
```

**Parameters:**
- `-vn` - no video
- `-acodec libmp3lame` - MP3 encoder
- `-q:a 2` - VBR quality level 2
- `-ar 44100` - 44.1 kHz sample rate (CD quality)
- `-ac 2` - stereo

### File Size Comparison

**Example:** 2-hour podcast

| Format | Bitrate | Size |
|--------|---------|------|
| M4A (AAC) | ~128 kbps | ~110 MB |
| **MP3 (VBR)** | **~190 kbps** | **~170 MB** |
| MP3 (320k) | 320 kbps | ~280 MB |

## Troubleshooting

### Conversion fails?

```bash
# Check FFmpeg installation
ffmpeg -version

# Install/update FFmpeg
brew install ffmpeg
```

### Light Phone still doesn't show episodes?

After conversion:
1. ✅ Check RSS feed has `type="audio/mpeg"`
2. ✅ Verify files end with `.mp3`
3. ✅ Validate feed at [Cast Feed Validator](https://castfeedvalidator.com)
4. ✅ Light Phone: Remove and re-add podcast

### Want to keep M4A?

```bash
# Edit utils/downloader.py, line 215:
keep_original=True  # Keep both M4A and MP3
```

## Configuration

**`.env` file:**
```env
# Automatically converts to MP3 regardless of this setting
AUDIO_FORMAT="mp3"

# Download quality (affects source quality before conversion)
AUDIO_QUALITY="best"
```

## Benefits

✅ **Universal Compatibility** - works everywhere  
✅ **Light Phone Support** - main requirement  
✅ **Automatic Process** - no manual steps  
✅ **High Quality** - VBR encoding  
✅ **Reasonable Size** - ~190kbps is efficient  

## Summary

Your podcast now:
1. Downloads audio from YouTube
2. **Automatically converts to MP3**
3. Generates RSS feed with MP3 URLs
4. Works with Light Phone and all other players

**No additional steps required!** 🎉

---

**Need help?** Check the logs for conversion details:
```bash
# Web server logs show conversion progress
tail -f web_*.log
```
