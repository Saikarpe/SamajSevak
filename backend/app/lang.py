"""Language / script detection and text normalisation.

Support levels:
  full    - English, Hinglish, Hindi and Marathi: classifier templates + risk lexicon exist
  partial - any other language: category and duplicates come from the multilingual
            embeddings only, risk keywords are not read, so the case goes to human review
"""
import re
import unicodedata

DEV = "ऀ-ॿ"
DEV_RE = re.compile(f"[{DEV}]+")
TOKEN_PATTERN = rf"(?u)[\w{DEV}]{{2,}}"  # \w alone splits Devanagari words at their vowel signs
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
SCRIPTS = [("Devanagari", 0x0900, 0x097F, None), ("Bengali", 0x0980, 0x09FF, "Bengali"),
           ("Gurmukhi", 0x0A00, 0x0A7F, "Punjabi"), ("Gujarati", 0x0A80, 0x0AFF, "Gujarati"),
           ("Odia", 0x0B00, 0x0B7F, "Odia"), ("Tamil", 0x0B80, 0x0BFF, "Tamil"), ("Telugu", 0x0C00, 0x0C7F, "Telugu"),
           ("Kannada", 0x0C80, 0x0CFF, "Kannada"), ("Malayalam", 0x0D00, 0x0D7F, "Malayalam"),
           ("Arabic", 0x0600, 0x06FF, "Urdu")]
MR_WORDS = set("आहे आहेत नाही झाले झाला झाली आमच्या आणि मध्ये पासून येत करा होत आले आलेली आलेला खूप असून असते तिथे".split())
MR_SUFFIX = ("मध्ये", "पासून", "ांना", "च्या", "जवळ", "ावर", "ामुळे", "साठी")
HI_WORDS = set("है हैं नहीं और में से का की के को रहा रही रहे हो गया गई था कर हमारे हमारी बहुत पर भी".split())
HINGLISH_WORDS = set("""nahi nahin hai hain paani pani mein ka ki ke se raha rahi rahe gaya gayi ho kar karo bahut wala
    wale band kharab aur aa ko par bhi abhi tak hamare hamari kya koi yahan kal raat subah""".split())


def norm(text: str) -> str:
    """NFC + ASCII digits, so lexicon lookups and the classifier see one spelling."""
    return unicodedata.normalize("NFC", text).translate(DEV_DIGITS)


def detect(text: str) -> dict:
    letters = [c for c in text if c.isalpha() or unicodedata.category(c).startswith("M")]
    counts = {name: sum(lo <= ord(c) <= hi for c in letters) for name, lo, hi, _ in SCRIPTS}
    script, n = max(counts.items(), key=lambda kv: kv[1])
    if n and n >= 0.3 * len(letters):
        if script != "Devanagari":
            name = next(lang for s, _, _, lang in SCRIPTS if s == script)
            return {"code": name[:2].lower(), "name": name, "script": script, "support": "partial"}
        toks = DEV_RE.findall(text)
        mr = sum(t in MR_WORDS or t.endswith(MR_SUFFIX) for t in toks)
        hi = sum(t in HI_WORDS for t in toks)
        return ({"code": "mr", "name": "Marathi", "script": "Devanagari", "support": "full"} if mr > hi else
                {"code": "hi", "name": "Hindi", "script": "Devanagari", "support": "full"})
    toks = re.findall(r"[a-z]+", text.lower())
    hits = sum(t in HINGLISH_WORDS for t in toks)
    if hits >= 2 and hits >= 0.15 * len(toks):
        return {"code": "hi-Latn", "name": "Hinglish", "script": "Latin", "support": "full"}
    return {"code": "en", "name": "English", "script": "Latin", "support": "full"}
