"""Generate original Arabic quotes from a curated bank of themes."""

import json
import os
import random
import re
import time
import unicodedata
from pathlib import Path

from google import genai
from google.genai import errors, types

ROOT = Path(__file__).resolve().parents[1]
POOL_FILE = ROOT / "data" / "inspiration_pool.json"
HISTORY_FILE = ROOT / "data" / "history.json"
HASHTAGS = os.getenv("CHANNEL_HASHTAGS") or "#سَطر #خواطر #حب #كراش #اقتباسات #مشاعر"
NICHE = os.getenv("CHANNEL_NICHE") or "الحب أو الكراش أو الإعجاب الخفي أو الشوق"
MODEL = "gemini-3.8-flash"


def _load_array(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, list):
        raise ValueError(f"{path} must contain a JSON array")
    return value


def _normalize(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().casefold()


def generate_quote():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required")

    pool = [item for item in _load_array(POOL_FILE) if isinstance(item, str) and item.strip()]
    history = _load_array(HISTORY_FILE)
    previous = {
        _normalize(item["quote"])
        for item in history
        if isinstance(item, dict) and isinstance(item.get("quote"), str)
    }
    topics = random.sample(pool, min(7, len(pool))) if pool else ["حب", "كراش", "شوق"]
    client = genai.Client(api_key=api_key)

    inspiration_block = ""
    if not os.getenv("CHANNEL_NICHE"):
        inspiration_block = "\n\nموضوعات للإلهام:\n" + "\n".join(f"- {topic}" for topic in topics)

    prompt = (
        f"اكتب خاطرة أو عبارة أصلية وجذابة في مجال: ({NICHE})، "
        "باللهجة العربية البسيطة الدافئة القريبة للقلب (مفهومة لكل العرب). "
        "الحد الأقصى 18 كلمة ومقسمة على سطرين أو ثلاثة بشكل أنيق. "
        "اكتب نصاً جديداً تماماً يلمس القارئ ولا تنقل أي صياغة حرفياً. "
        "أعد JSON فقط بمفتاحين: quote وcaption. "
        "اجعل caption وصفاً قصيراً معبّراً دون أي هاشتاجات؛ ستضاف الهاشتاجات تلقائياً: "
        f"{HASHTAGS}.{inspiration_block}"
    )

    for attempt in range(10):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
        except errors.APIError:
            # انتظار متزايد (10s, 20s, 30s...) لتجاوز أي ضغط مؤقت على سيرفرات جوجل
            time.sleep(min(60, 10 * (attempt + 1)))
            continue

        try:
            result = json.loads(response.text or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(result, dict):
            continue
        quote = result.get("quote")
        caption = result.get("caption")
        if not isinstance(quote, str) or not isinstance(caption, str):
            continue
        quote = quote.strip()
        if len(quote.split()) > 18 or len(quote.splitlines()) > 3 or not quote:
            continue
        if _normalize(quote) in previous:
            continue
        result["quote"] = quote
        description = re.sub(r"(?<!\w)#[\w\u0600-\u06ff]+", "", caption)
        description = re.sub(r"\s+", " ", description).strip()
        result["caption"] = f"{description} {HASHTAGS}".strip()
        return result
    raise RuntimeError("Gemini did not produce a valid, non-repeated quote after 10 attempts")


def record_quote(quote):
    """Persist a quote only after the video has been successfully published."""
    history = _load_array(HISTORY_FILE)
    if _normalize(quote) in {
        _normalize(item["quote"])
        for item in history
        if isinstance(item, dict) and isinstance(item.get("quote"), str)
    }:
        return
    history.append({"quote": quote})
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = HISTORY_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(HISTORY_FILE)
