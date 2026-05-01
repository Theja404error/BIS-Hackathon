"""
Translates rationale text into Hindi/Tamil for MSE accessibility.

Safety: IS codes (e.g., "IS 12269:1987") are NEVER passed through translation —
they are masked, the rationale is translated, then the codes are restored.
This prevents the LLM from corrupting code numbers via "translation".
"""
import re
from typing import List, Dict
from src.llm import generate

IS_CODE_RE = re.compile(r"\bIS\s*\d{1,5}(?::\d{4})?(?:\s*\(Part\s*\d+\))?\b", re.IGNORECASE)


SUPPORTED = {
    "English": None,
    "Hindi": "Hindi (हिन्दी)",
    "Tamil": "Tamil (தமிழ்)",
}


def _mask_codes(text: str) -> tuple:
    """Replace IS codes with placeholders. Returns (masked_text, code_list)."""
    codes = IS_CODE_RE.findall(text)
    masked = text
    for i, code in enumerate(codes):
        masked = masked.replace(code, f"[[CODE_{i}]]", 1)
    return masked, codes


def _unmask_codes(text: str, codes: List[str]) -> str:
    """Put IS codes back."""
    for i, code in enumerate(codes):
        text = text.replace(f"[[CODE_{i}]]", code)
    return text


def translate_text(text: str, target_lang: str) -> str:
    """Translate while preserving IS codes verbatim."""
    if target_lang == "English" or not text:
        return text
    if target_lang not in SUPPORTED:
        return text

    masked, codes = _mask_codes(text)
    prompt = f"""Translate the following English text to {SUPPORTED[target_lang]}.
Keep any [[CODE_N]] placeholders EXACTLY as they appear — do not translate or modify them.
Respond with ONLY the translated text, no preamble, no explanation, no quotes.

Text to translate:
{masked}"""
    try:
        translated = generate(prompt, max_tokens=400).strip()
        # Strip surrounding quotes if model added them
        if translated.startswith('"') and translated.endswith('"'):
            translated = translated[1:-1]
        return _unmask_codes(translated, codes)
    except Exception:
        return text  # fail safe: return English


def translate_rationales(rationales: List[Dict], target_lang: str) -> List[Dict]:
    """Translate the rationale field in each item; standard codes untouched."""
    if target_lang == "English":
        return rationales
    out = []
    for r in rationales:
        out.append({
            "standard": r["standard"],  # never translated
            "rationale": translate_text(r.get("rationale", ""), target_lang),
        })
    return out