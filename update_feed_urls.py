#!/usr/bin/env python3
"""Update RSS feed with GitHub Releases URLs."""
import xml.etree.ElementTree as ET
from pathlib import Path

rss_file = Path("podcast/rss.xml")
new_base_url = "https://github.com/2vlad/vlad-podcast/releases/download/media-files"

print(f"📝 Updating RSS feed URLs...")
print(f"   New base URL: {new_base_url}")

# Parse RSS
tree = ET.parse(rss_file)
root = tree.getroot()

# Find all enclosure elements
count = 0
for enclosure in root.findall('.//enclosure'):
    old_url = enclosure.get('url')
    if old_url:
        # Extract filename
        filename = old_url.split('/')[-1]
        new_url = f"{new_base_url}/{filename}"
        enclosure.set('url', new_url)
        print(f"   Updated: {filename}")
        count += 1

# Save
tree.write(rss_file, encoding='UTF-8', xml_declaration=True)
print(f"\n✅ Updated {count} episode(s)")
print(f"📁 Saved to: {rss_file}")
