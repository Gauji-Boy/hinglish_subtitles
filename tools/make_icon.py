"""
make_icon.py - Generates a professional Neo-Brutalist app icon for HinglishSubtitles.exe
"""
from PIL import Image, ImageDraw

def create_icon():
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []

    for w, h in sizes:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Scale factor
        s = w / 256.0

        # Background rounded/sharp rect with dark border
        pad = int(8 * s)
        shadow_off = int(12 * s)

        # White/cyan drop shadow
        draw.rectangle([pad + shadow_off, pad + shadow_off, w - pad, h - pad], fill=(248, 250, 252, 255))
        # Yellow face
        draw.rectangle([pad, pad, w - pad - shadow_off, h - pad - shadow_off], fill=(250, 204, 21, 255), outline=(0, 0, 0, 255), width=max(1, int(6 * s)))

        # CC / Subtitle glyph inside
        bx = pad + int(24 * s)
        by = pad + int(40 * s)
        bw = w - pad - shadow_off - int(24 * s)
        bh = h - pad - shadow_off - int(40 * s)

        # Draw black inner card
        draw.rectangle([bx, by, bw, bh], fill=(12, 13, 16, 255), outline=(0, 0, 0, 255), width=max(1, int(4 * s)))

        # Draw subtitle lines in white and cyan
        line_pad = int(16 * s)
        lh = int(10 * s)
        gap = int(14 * s)

        # Line 1: White
        draw.rectangle([bx + line_pad, by + line_pad, bw - line_pad, by + line_pad + lh], fill=(255, 255, 255, 255))
        # Line 2: Cyan
        draw.rectangle([bx + line_pad, by + line_pad + gap + lh, bx + line_pad + int((bw - bx - line_pad * 2) * 0.65), by + line_pad + gap + lh * 2], fill=(56, 189, 248, 255))

        images.append(img)

    images[0].save("app_icon.ico", format="ICO", sizes=[(im.width, im.height) for im in images])
    print("[*] Successfully generated app_icon.ico")

if __name__ == "__main__":
    create_icon()
