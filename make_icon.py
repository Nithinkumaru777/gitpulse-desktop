"""
Generate the GitPulse icon (gitpulse_icon.ico).
Requires: pip install pillow
"""

from PIL import Image, ImageDraw


def create_logo():
    size = (256, 256)
    img = Image.new("RGB", size, color=(30, 30, 30))
    d = ImageDraw.Draw(img)

    # GitHub contribution green
    green = (57, 211, 83)

    # Heartbeat / pulse line
    points = [
        (20, 128), (80, 128),       # flat start
        (100, 60), (128, 196),       # spike up, dip down
        (148, 128), (236, 128),      # flat end
    ]
    d.line(points, fill=green, width=24)

    # Active status dot (top-right)
    d.ellipse([200, 20, 230, 50], fill=green)

    # Save as .ico
    img.save("gitpulse_icon.ico", format="ICO", sizes=[(256, 256)])
    print("Logo created: gitpulse_icon.ico")


if __name__ == "__main__":
    create_logo()
