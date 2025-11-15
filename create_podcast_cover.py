#!/usr/bin/env python3
"""
Create a simple podcast cover image (1400x1400px).
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_podcast_cover(
    output_path: Path,
    title: str = "Влад Слушает",
    subtitle: str = "Записи для прогулок",
    size: int = 1400,
    bg_color: str = "#1d1d1f",
    text_color: str = "#ffffff"
):
    """
    Create a simple podcast cover image.
    
    Args:
        output_path: Where to save the image
        title: Main title text
        subtitle: Subtitle text
        size: Image size (square)
        bg_color: Background color
        text_color: Text color
    """
    # Create image
    img = Image.new('RGB', (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fall back to default if not available
    try:
        # Try common system fonts
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 180)
        subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
    except:
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 180)
            subtitle_font = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 80)
        except:
            # Fall back to default font
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
    
    # Calculate text positions (centered)
    # Get text bounding boxes
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_height = subtitle_bbox[3] - subtitle_bbox[1]
    
    # Center positions
    title_x = (size - title_width) // 2
    title_y = (size - title_height) // 2 - 80
    subtitle_x = (size - subtitle_width) // 2
    subtitle_y = title_y + title_height + 60
    
    # Draw text
    draw.text((title_x, title_y), title, fill=text_color, font=title_font)
    draw.text((subtitle_x, subtitle_y), subtitle, fill=text_color, font=subtitle_font, opacity=0.7)
    
    # Add decorative elements (optional)
    # Draw a subtle circle
    circle_radius = 500
    circle_center = (size // 2, size // 2)
    circle_bbox = [
        circle_center[0] - circle_radius,
        circle_center[1] - circle_radius,
        circle_center[0] + circle_radius,
        circle_center[1] + circle_radius
    ]
    draw.ellipse(circle_bbox, outline=text_color, width=3)
    
    # Save image
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, 'JPEG', quality=95)
    print(f"✓ Created podcast cover: {output_path}")
    print(f"  Size: {size}x{size}px")
    print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == '__main__':
    import sys
    
    # Output to docs directory for GitHub Pages
    output = Path(__file__).parent / 'docs' / 'podcast-cover.jpg'
    
    try:
        create_podcast_cover(
            output_path=output,
            title="Влад Слушает",
            subtitle="Записи для прогулок"
        )
        print(f"\n✅ Podcast cover created successfully!")
        print(f"🔗 GitHub Pages URL: https://2vlad.github.io/vlad-podcast/podcast-cover.jpg")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTrying to install Pillow...")
        import subprocess
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'Pillow'])
        print("\nPlease run this script again after installing Pillow.")
        sys.exit(1)
