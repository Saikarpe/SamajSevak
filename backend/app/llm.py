"""Optional LLM enhancement (Gemini or OpenAI). The platform works fully offline;
when an API key is configured, the LLM drafts empathetic citizen replies and
officer briefs grounded in the local ML analysis."""
import base64
import json
import os
import re

import httpx

from app.knowledge import CATEGORY_NAMES, PRIORITY_NAMES, WARD_NAMES_DEVANAGARI

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")


def provider():
    return "gemini" if GEMINI_KEY else "openai" if OPENAI_KEY else None


def _prompt(g: dict) -> str:
    a = g.get("analysis") or {}
    rec = a.get("recommendation", {})
    return (
        "You are a helpful municipal grievance officer in India. Using the analysis below, write:\n"
        "1) CITIZEN_REPLY: a short, empathetic, specific reply to the citizen (max 90 words), in the same language "
        "style as the complaint, with the tracking ID and expected timeline. No false promises.\n"
        "2) OFFICER_BRIEF: 3 crisp bullet points for the field officer.\n\n"
        f"Tracking ID: {g['id']}\nComplaint: {g['text']}\nWard: {g.get('ward')}\nCategory: {g.get('category')}\n"
        f"Department: {g.get('department')}\nPriority: {g.get('priority_level')} ({g.get('priority_score')}/100)\n"
        f"Action plan: {rec.get('action_plan')}\nEstimated hours: {rec.get('estimated_resolution_hours')}\n"
    )


# (reply, hours, days, default salutation) for complaints written in Hindi / Marathi
LOCAL_REPLY = {
    "hi": ("प्रिय {name},\n\nसमस्या की सूचना देने के लिए धन्यवाद। आपकी शिकायत {id} ({category}, {ward}) {department} के पास दर्ज "
           "कर ली गई है और इसे {priority} प्राथमिकता दी गई है। अनुमानित समाधान समय लगभग {when} है। आप SamajSevak पोर्टल पर "
           "अपनी आईडी से स्थिति देख सकते हैं।\n\nसादर,\nSamajSevak शिकायत कक्ष", "{} घंटे", "{} दिन", "नागरिक"),
    "mr": ("प्रिय {name},\n\nसमस्या कळवल्याबद्दल धन्यवाद. आपली तक्रार {id} ({category}, {ward}) {department} कडे नोंदवण्यात "
           "आली असून तिला {priority} प्राधान्य देण्यात आले आहे. अंदाजे निराकरण कालावधी सुमारे {when} आहे. SamajSevak पोर्टलवर "
           "आपल्या आयडीद्वारे स्थिती पाहू शकता.\n\nआपला,\nSamajSevak तक्रार कक्ष", "{} तास", "{} दिवस", "नागरिक"),
}


def template_reply(g: dict) -> str:
    a = g.get("analysis") or {}
    rec = a.get("recommendation", {})
    hrs = rec.get("estimated_resolution_hours") or 48
    code = (a.get("language") or {}).get("code")
    if code in LOCAL_REPLY:
        text, hours, days, citizen = LOCAL_REPLY[code]
        return text.format(
            name=g.get("citizen_name") or citizen, id=g["id"], department=g.get("department"),
            category=CATEGORY_NAMES[code].get(g.get("category"), g.get("category")),
            ward=WARD_NAMES_DEVANAGARI.get(g.get("ward"), g.get("ward") or ""),
            priority=PRIORITY_NAMES[code].get(g.get("priority_level"), g.get("priority_level")),
            when=hours.format(round(hrs)) if hrs < 48 else days.format(round(hrs / 24)))
    when = f"{round(hrs)} hours" if hrs < 48 else f"{round(hrs / 24)} days"
    first = (rec.get("action_plan") or ["inspect the issue"])[0]
    first = first[0].lower() + first[1:]
    name = g.get("citizen_name") or "Citizen"
    return (
        f"Dear {name},\n\nThank you for reporting this issue. Your grievance {g['id']} regarding "
        f"{(g.get('category') or 'the issue').lower()} in {g.get('ward') or 'your area'} has been registered with "
        f"the {g.get('department')} and marked as {g.get('priority_level')} priority. "
        f"Our team will {first}. The expected resolution time is about {when}. "
        f"You can track live status using your ID on the SamajSevak portal.\n\nRegards,\nSamajSevak Grievance Cell"
    )


def _ask(p: str, prompt: str, image: tuple | None = None) -> str:
    """One LLM call. image = (raw bytes, mime type) for the photo check."""
    b64 = base64.b64encode(image[0]).decode() if image else None
    if p == "gemini":
        parts = [{"text": prompt}] + ([{"inline_data": {"mime_type": image[1], "data": b64}}] if image else [])
        r = httpx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            params={"key": GEMINI_KEY}, timeout=20, json={"contents": [{"parts": parts}]})
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    content = prompt if not image else [
        {"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:{image[1]};base64,{b64}"}}]
    r = httpx.post("https://api.openai.com/v1/chat/completions", timeout=20,
                   headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                   json={"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                         "messages": [{"role": "user", "content": content}]})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def draft(g: dict) -> dict:
    p = provider()
    if not p:
        return {"provider": "template", "text": template_reply(g)}
    try:
        return {"provider": p, "text": _ask(p, _prompt(g)).strip()}
    except Exception as e:  # never break the workflow
        return {"provider": "template", "text": template_reply(g), "warning": f"LLM unavailable: {e.__class__.__name__}"}


def check_photo(raw: bytes, mime: str, g: dict) -> dict | None:
    """Ask a vision model whether the citizen's photo shows the reported problem.
    Advisory only: it never changes category, priority or routing. None without an API key."""
    p = provider()
    if not p:
        return None
    prompt = (
        "A citizen attached this photo to a municipal complaint. Reply with JSON only, no prose: "
        '{"matches": true or false, "seen": "what the photo shows, at most 15 words", "severity": "low|medium|high"}\n'
        f"Complaint: {g['text']}\nCategory: {g.get('category')}")
    try:
        out = json.loads(re.search(r"\{.*\}", _ask(p, prompt, (raw, mime)), re.S).group(0))
        return {"provider": p, "matches": bool(out.get("matches")), "seen": str(out.get("seen", ""))[:200],
                "severity": out.get("severity") if out.get("severity") in ("low", "medium", "high") else None}
    except Exception as e:
        return {"provider": p, "error": e.__class__.__name__}
