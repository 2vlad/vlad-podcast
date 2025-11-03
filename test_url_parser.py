#!/usr/bin/env python3
"""
Quick test for YouTube URL parsing - including live and shorts
"""

from utils.url_processor import parse_url

test_urls = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://www.youtube.com/live/NX7p0SAbk_M?si=hMBeoc95sefBitEU",
    "https://www.youtube.com/shorts/abc123XYZ-_",
    "https://www.youtube.com/embed/dQw4w9WgXcQ",
    "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
]

print("Testing YouTube URL parser:\n")

for url in test_urls:
    try:
        parsed = parse_url(url)
        print(f"✅ {url}")
        print(f"   Video ID: {parsed.video_id}")
        print(f"   Normalized: {parsed.normalized_url}\n")
    except Exception as e:
        print(f"❌ {url}")
        print(f"   Error: {e}\n")
