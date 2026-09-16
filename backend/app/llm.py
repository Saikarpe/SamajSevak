"""Optional LLM enhancement (Gemini or OpenAI). The platform works fully offline;
when an API key is configured, the LLM drafts empathetic citizen replies and
officer briefs grounded in the local ML analysis."""
import os

import httpx

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


def template_reply(g: dict) -> str:
    a = g.get("analysis") or {}
    rec = a.get("recommendation", {})
    hrs = rec.get("estimated_resolution_hours") or 48
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


def draft(g: dict) -> dict:
    p = provider()
    if not p:
        return {"provider": "template", "text": template_reply(g)}
    try:
        if p == "gemini":
            r = httpx.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                params={"key": GEMINI_KEY}, timeout=20,
                json={"contents": [{"parts": [{"text": _prompt(g)}]}]})
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            r = httpx.post("https://api.openai.com/v1/chat/completions", timeout=20,
                           headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                           json={"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                                 "messages": [{"role": "user", "content": _prompt(g)}]})
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
        return {"provider": p, "text": text.strip()}
    except Exception as e:  # never break the workflow
        return {"provider": "template", "text": template_reply(g), "warning": f"LLM unavailable: {e.__class__.__name__}"}
