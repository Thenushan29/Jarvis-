"""Screen vision via Groq's multimodal Llama 4 Scout."""
import base64
import io

from groq import Groq

from ..config import GROQ_API_KEY, GROQ_VISION_MODEL

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def _grab_screenshot_b64() -> str:
    """Capture full screen, return base64-encoded PNG."""
    from PIL import ImageGrab, Image
    try:
        img = ImageGrab.grab(all_screens=True)
    except TypeError:
        img = ImageGrab.grab()
    max_side = 1600
    if max(img.size) > max_side:
        ratio = max_side / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.standard_b64encode(buf.getvalue()).decode("ascii")


def describe_screen(question: str = "") -> str:
    """Take a screenshot and ask the vision model about it."""
    try:
        b64 = _grab_screenshot_b64()
    except Exception as e:
        return f"Could not capture screen: {e}"

    prompt = question.strip() or "Describe what's on this screen in 1-2 short sentences."
    try:
        resp = _get_client().chat.completions.create(
            model=GROQ_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }],
            max_tokens=400,
            temperature=0.4,
        )
        return (resp.choices[0].message.content or "").strip() or "I couldn't make out the screen."
    except Exception as e:
        return f"Vision call failed: {e}"
