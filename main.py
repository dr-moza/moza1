"""Entry point for automated and custom TikTok quote video publishing."""

import logging
import os

from src.generator import HASHTAGS, generate_quote, record_quote
from src.tiktok_uploader import publish_video
from src.video_maker import create_video

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    custom_quote = os.environ.get("CUSTOM_QUOTE", "").strip()
    if custom_quote:
        logging.info("Running in custom quote mode with image 1")
        quote_text = custom_quote
        caption = f"كلام من القلب ✨ {HASHTAGS}"
        video_path = create_video(quote_text, use_custom_image=True)
    else:
        post = generate_quote()
        quote_text = post["quote"]
        caption = post["caption"]
        video_path = create_video(quote_text, use_custom_image=False)

    try:
        publish_id = publish_video(video_path, caption)
        logging.info("TikTok accepted video (publish_id=%s)", publish_id)
        record_quote(quote_text)
    finally:
        video_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
