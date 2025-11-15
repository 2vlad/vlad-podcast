# YouTube to Podcast Converter

Convert YouTube videos to a personal podcast RSS feed for offline listening on your podcast app.

## Features

- ✅ Download audio from YouTube videos (best quality)
- ✅ **Auto-split long videos** (>1 hour) into separate episodes
- ✅ Convert to M4A (AAC) or MP3 format
- ✅ Generate RSS 2.0 feed with iTunes podcast tags
- ✅ Automatic duplicate detection (no duplicate episodes)
- ✅ Batch processing (multiple URLs at once)
- ✅ Custom podcast metadata (title, author, description)
- ✅ Environment-based configuration

## Requirements

- Python 3.9+
- ffmpeg (for audio conversion)
- yt-dlp (for YouTube downloads)

## Installation

### 1. Install System Dependencies

**macOS (using Homebrew):**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/youtube-podcast.git
cd youtube-podcast

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configure

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` and set **required** variables:

```bash
# REQUIRED: Your podcast feed URL (where you'll host it)
SITE_URL="https://yourusername.github.io/my-podcast"

# REQUIRED: Where your media files will be accessible
MEDIA_BASE_URL="https://yourusername.github.io/my-podcast/media"

# Optional: Customize podcast metadata
PODCAST_TITLE="My YouTube Podcast"
PODCAST_AUTHOR="Your Name"
PODCAST_DESCRIPTION="Personal podcast feed from YouTube videos"

# Optional: Audio format (m4a or mp3)
AUDIO_FORMAT="m4a"
```

## Usage

### Basic Usage

Convert a single YouTube video:

```bash
python yt2pod.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Batch Processing

Process multiple videos at once:

```bash
python yt2pod.py \
  "https://www.youtube.com/watch?v=VIDEO_ID1" \
  "https://youtu.be/VIDEO_ID2" \
  "https://www.youtube.com/watch?v=VIDEO_ID3"
```

### Output

The script will:
1. Download audio from each video
2. Convert to your configured format (M4A or MP3)
3. Extract metadata (title, description, duration, thumbnail)
4. Update `podcast/rss.xml` with new episodes

```
podcast/
├── media/
│   ├── VIDEO_ID1.m4a
│   ├── VIDEO_ID2.m4a
│   └── VIDEO_ID3.m4a
└── rss.xml
```

## Subscribe to Your Podcast

### Option 1: GitHub Pages (Recommended for beginners)

1. Initialize git repository (if not already):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. Create GitHub repository and push:
   ```bash
   git remote add origin https://github.com/yourusername/my-podcast.git
   git branch -M main
   git push -u origin main
   ```

3. Enable GitHub Pages:
   - Go to repository Settings → Pages
   - Source: Deploy from branch `main` → `/ (root)`
   - Save

4. Your feed will be available at:
   ```
   https://yourusername.github.io/my-podcast/podcast/rss.xml
   ```

5. Subscribe in your podcast app using this URL

### Option 2: Self-Hosted

Upload the `podcast/` directory to your web server and point your podcast app to:
```
https://yourdomain.com/podcast/rss.xml
```

### Option 3: Local Testing

For testing, you can use a local web server:

```bash
cd podcast
python3 -m http.server 8000
```

Then subscribe using: `http://localhost:8000/rss.xml`

⚠️ **Note:** Local URLs only work while your computer is on and the server is running.

## Configuration Options

All configuration is done via environment variables (set in `.env` file):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SITE_URL` | ✅ Yes | - | Base URL for your podcast site |
| `MEDIA_BASE_URL` | ✅ Yes | - | Base URL for media files |
| `AUDIO_FORMAT` | No | `m4a` | Audio format: `m4a` or `mp3` |
| `AUDIO_QUALITY` | No | `best` | Audio quality |
| `FEED_MAX_ITEMS` | No | `50` | Max episodes in feed |
| `PODCAST_TITLE` | No | `YouTube to Podcast` | Podcast title |
| `PODCAST_DESCRIPTION` | No | (default) | Podcast description |
| `PODCAST_AUTHOR` | No | `Your Name` | Author name |
| `PODCAST_LANGUAGE` | No | `en` | Language code |
| `PODCAST_CATEGORY` | No | `Technology` | iTunes category |

## Supported URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://m.youtube.com/watch?v=VIDEO_ID`
- URLs with additional parameters (e.g., `&t=10s`)

## Troubleshooting

### "Configuration error: SITE_URL is required"

You need to create a `.env` file with `SITE_URL` and `MEDIA_BASE_URL` set. See [Configuration](#3-configure).

### "ffmpeg not found"

Install ffmpeg:
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### Video download fails

- Check if the video is available and not private/age-restricted
- Update yt-dlp: `pip install --upgrade yt-dlp`
- Some videos may require authentication (not supported in v1)

### Episode doesn't appear in podcast app

- Verify your RSS feed is accessible at `SITE_URL/rss.xml`
- Check feed validity: https://podba.se/validate/
- Some apps cache feeds - try refreshing or re-adding the feed

## Project Structure

```
youtube-podcast/
├── yt2pod.py           # Main script
├── config.py           # Configuration management
├── utils/              # Utility modules
│   ├── downloader.py   # YouTube audio downloader
│   ├── url_processor.py # URL parsing and validation
│   ├── rss_manager.py  # RSS feed generation
│   └── logger.py       # Logging setup
├── podcast/            # Output directory
│   ├── media/          # Audio files
│   └── rss.xml         # RSS feed
├── requirements.txt    # Python dependencies
├── .env                # Your configuration
└── .env.example        # Configuration template
```

## How It Works

1. **URL Processing**: Validates and extracts video IDs from YouTube URLs
2. **Download**: Uses yt-dlp to download best quality audio
3. **Conversion**: ffmpeg converts to your preferred format (M4A/MP3)
4. **Metadata**: Extracts title, description, duration, thumbnail
5. **RSS Generation**: Creates/updates RSS 2.0 feed with iTunes tags
6. **Deduplication**: Checks existing episodes to avoid duplicates

## Limitations (v1)

- No playlist support (individual videos only)
- No age-restricted or private videos
- No automatic YouTube subscription monitoring
- Basic error recovery

## Future Enhancements

- Playlist support
- Auto-upload to cloud storage (S3/R2)
- YouTube channel subscription monitoring
- ID3 tags for MP3 files
- Volume normalization
- Web UI

## Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see LICENSE file for details.

## Disclaimer

This tool is for personal use. Respect YouTube's Terms of Service and content creators' rights. Do not redistribute content without permission.

## Additional Documentation

- [Long Video Splitting Guide](LONG_VIDEO_SPLITTING.md) - Automatic splitting of videos >1 hour into separate episodes
- [Quick Start Guide](QUICKSTART.md) - Get started quickly
- [Complete Guide](COMPLETE_GUIDE.md) - Full documentation
- [GitHub Pages Setup](GITHUB_PAGES_SETUP.md) - Deploy to GitHub Pages
