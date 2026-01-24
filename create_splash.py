from PIL import Image, ImageDraw, ImageFont
import os

def create_splash():
    # Create assets directory if it doesn't exist
    if not os.path.exists("assets"):
        os.makedirs("assets")

    # Image size
    width, height = 500, 300
    background_color = "#2C3E50"  # Dark blue-gray
    text_color = "#ECF0F1"       # White-ish
    accent_color = "#E74C3C"     # Red

    # Create image
    image = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(image)

    # Load font (default to simple one if arial not found, but try to find a system font)
    try:
        # Try to use Arial on Windows
        title_font = ImageFont.truetype("arial.ttf", 36)
        subtitle_font = ImageFont.truetype("arial.ttf", 18)
        footer_font = ImageFont.truetype("arial.ttf", 12)
    except IOError:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        footer_font = ImageFont.load_default()

    # Draw Title
    title_text = "HONDA"
    # Get text bounding box
    bbox = draw.textbbox((0, 0), title_text, font=title_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, 80), title_text, font=title_font, fill=accent_color)

    # Draw Subtitle
    sub_text = "FBR INVOICE UPLOADER"
    bbox = draw.textbbox((0, 0), sub_text, font=subtitle_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, 130), sub_text, font=subtitle_font, fill=text_color)

    # Draw Loading text
    loading_text = "Loading application..."
    bbox = draw.textbbox((0, 0), loading_text, font=footer_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, 250), loading_text, font=footer_font, fill="#95A5A6")

    # Save
    image.save("assets/splash.png")
    print("Splash screen created at assets/splash.png")

if __name__ == "__main__":
    create_splash()
