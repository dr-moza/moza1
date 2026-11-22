"""Render a 9:16 quote video using Pillow and FFmpeg."""

import os
import random
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1080, 1920


def _choose(directory, suffixes):
    if not directory.exists():
        return None
    if isinstance(suffixes, str):
        suffixes = (suffixes,)
    files = [
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in suffixes and f.stat().st_size > 1024
    ]
    return random.choice(files) if files else None


def _find_custom_image():
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = ROOT / "assets" / f"1{ext}"
        if candidate.exists() and candidate.stat().st_size > 1024:
            return candidate
    return None


def _get_random_arabic_font(size):
    fonts_dir = ROOT / "assets" / "fonts"
    available_fonts = []
    if fonts_dir.exists():
        available_fonts = [
            f for f in fonts_dir.iterdir()
            if f.is_file() and f.suffix.lower() in (".ttf", ".otf") and f.stat().st_size > 10_000
        ]

    if available_fonts:
        chosen = random.choice(available_fonts)
        font = ImageFont.truetype(str(chosen), size=size)
        try:
            font.set_variation_by_axes([800])
        except Exception:
            pass
        return font

    fallback = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    if fallback.exists():
        return ImageFont.truetype(str(fallback), size=size)
    return ImageFont.load_default()


def _clean_lines(text):
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _render_overlay(quote, output_png):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=(0, 0, 0, 115))

    quote_font = _get_random_arabic_font(76)
    sig_font = _get_random_arabic_font(42)

    clean_quote = _clean_lines(quote)
    signature = os.getenv("CHANNEL_SIGNATURE") or "@satr.words  |  سَطر"

    bbox = draw.multiline_textbbox(
        (0, 0),
        clean_quote,
        font=quote_font,
        spacing=34,
        align="center",
        direction="rtl",
        stroke_width=3,
    )
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (WIDTH - text_w) / 2
    y = (HEIGHT - text_h) / 2 - 50

    draw.multiline_text(
        (x + 4, y + 6),
        clean_quote,
        font=quote_font,
        fill=(0, 0, 0, 190),
        spacing=34,
        align="center",
        direction="rtl",
    )
    draw.multiline_text(
        (x, y),
        clean_quote,
        font=quote_font,
        fill=(255, 255, 255, 255),
        spacing=34,
        align="center",
        direction="rtl",
        stroke_width=3,
        stroke_fill=(0, 0, 0, 220),
    )

    sig_bbox = draw.textbbox((0, 0), signature, font=sig_font, direction="rtl", stroke_width=2)
    sig_w = sig_bbox[2] - sig_bbox[0]
    draw.text(
        ((WIDTH - sig_w) / 2, y + text_h + 85),
        signature,
        font=sig_font,
        fill=(235, 235, 235, 225),
        direction="rtl",
        stroke_width=2,
        stroke_fill=(0, 0, 0, 200),
    )

    img.save(output_png, "PNG")


def create_video(quote, output_path=None, use_custom_image=False):
    if output_path is None:
        tmp_dir = Path(tempfile.mkdtemp(prefix="satr_video_"))
        output_path = tmp_dir / "quote.mp4"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    overlay_png = output_path.with_suffix(".png")
    _render_overlay(quote, overlay_png)

    custom_img = _find_custom_image() if use_custom_image else None
    background = None if custom_img else _choose(ROOT / "assets" / "backgrounds", (".mp4", ".mov", ".webm"))
    music = _choose(ROOT / "assets" / "music", (".mp3", ".m4a", ".wav"))
    cover_img = ROOT / "assets" / "cover.png"
    has_cover = (not use_custom_image) and cover_img.exists() and cover_img.stat().st_size > 1024
    duration = random.randint(8, 11)

    cmd = ["ffmpeg", "-y"]
    if custom_img:
        cmd += ["-loop", "1", "-t", str(duration), "-i", str(custom_img)]
    elif background:
        cmd += ["-stream_loop", "-1", "-i", str(background)]
    else:
        cmd += ["-f", "lavfi", "-i", f"color=c=0x121218:s={WIDTH}x{HEIGHT}:d={duration}:r=25"]

    cmd += ["-i", str(overlay_png)]

    audio_idx = 2
    if has_cover:
        cmd += ["-i", str(cover_img)]
        audio_idx = 3

    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]

    if has_cover:
        filter_complex = (
            f"[0:v]fps=25,scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},setsar=1[bg];"
            f"[bg][1:v]overlay=0:0[txt];"
            f"[2:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},setsar=1[cov];"
            f"[txt][cov]overlay=0:0:enable='lte(t,0.3)'[v]"
        )
    else:
        filter_complex = (
            f"[0:v]fps=25,scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},setsar=1[bg];"
            f"[bg][1:v]overlay=0:0[v]"
        )

    cmd += ["-filter_complex", filter_complex, "-map", "[v]"]

    if music:
        cmd += ["-map", f"{audio_idx}:a", "-shortest"]

    cmd += [
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_path),
    ]

    subprocess.run(cmd, check=True)
    if overlay_png.exists():
        overlay_png.unlink()
    return output_path
