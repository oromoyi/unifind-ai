"""AI endpoints powered by Google Gemini Flash with robust local fallbacks.

Endpoints
---------
POST /api/ai/chat            – conversational assistant (knows about UniFind AI)
POST /api/ai/analyze-image   – image → auto-fill item details (title, category, color, brand)
POST /api/ai/search          – natural-language query → structured search filters
POST /api/ai/explain-match   – richer human explanation for a matching result
"""
import base64
import io
import json
import os
import re
import urllib.request
import urllib.error
from PIL import Image

from flask import Blueprint, jsonify, request

from ..security import error, rate_limit  # type: ignore[import]
from ..models import Category, Location, MatchingResult  # type: ignore[import]
from ..extensions import db  # type: ignore[import]

bp = Blueprint("ai", __name__, url_prefix="/api/ai")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key={key}"
)

SYSTEM_CONTEXT = """You are the AI assistant for UniFind AI, a university lost-and-found platform.

Key facts about this system:
- Students can report lost items and browse found items.
- Finders (staff/students) register found items and hand them to campus security.
- An AI matching engine compares lost reports with found items using category, description, colour, brand, location and photo similarity.
- Claims are verified through private questions; officers approve or reject them.
- After approval, the student gets a unique handover code to collect their item.
- The system is for a university campus and is meant for educational/demonstration purposes.

Contact: Phone 0922750429, Email deressafufa54@gmail.com

Be concise, friendly and helpful. If asked about something unrelated to the system, politely redirect to lost-and-found topics.
"""

# ---------------------------------------------------------------------------
# Built-in rule-based fallback — works with NO API key
# ---------------------------------------------------------------------------
_FALLBACK_KB = [
    (["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"],
     "Hello! 👋 I'm the UniFind AI assistant. I can help you with lost & found questions, reporting items, claims, and how the system works. What would you like to know?"),
    (["how are you", "how r u", "what's up", "sup"],
     "I'm doing great and ready to help! 😊 Ask me anything about UniFind AI."),
    (["report lost", "lost item", "lost something", "i lost", "missing item", "how to report"],
     "To report a lost item:\n1. Register or log in as a **Student**.\n2. Go to **Report lost item** in the dashboard.\n3. Fill in the title, category, location, date, colour and description.\n4. Upload a photo if you have one — it helps the AI match engine.\n5. Submit! The system will immediately search for matching found items and notify you."),
    (["report found", "found item", "found something", "i found", "register found"],
     "To register a found item:\n1. Register or log in as a **Finder** (or Officer/Admin).\n2. Go to **Register found item**.\n3. Add a public description plus a **private verification question** only the true owner would know.\n4. Hand the item to Campus Security.\n5. After officer approval it goes live and the matching engine runs automatically."),
    (["how does match", "matching", "how match work", "ai match", "match engine"],
     "The matching engine scores every (lost, found) pair using 6 signals:\n• **Category** — same category?\n• **Description** — TF-IDF text similarity\n• **Colour / Brand** — colour family and brand agreement\n• **Location** — same place or nearby on the campus grid\n• **Date** — found shortly after it was lost?\n• **Photo** — colour histogram comparison\n\nScores are 0–100. The engine only *suggests* matches — a human officer always makes the final decision."),
    (["claim", "how to claim", "claim item", "ownership"],
     "To claim a found item:\n1. Browse found items or open a suggested match.\n2. Press **'This is mine'** on the item page.\n3. Describe the item in detail and answer the private verification question set by the finder.\n4. An officer reviews your claim. You have **3 attempts** before you must visit the office in person.\n5. If approved, you receive a **handover code** — bring it and your student ID to collect the item."),
    (["handover", "collect", "pick up", "handover code"],
     "After your claim is approved:\n• You'll get a notification with a unique **handover code**.\n• Go to the Lost-and-Found office with your **student/staff ID**.\n• Give the officer the handover code.\n• The officer completes the handover and you receive a receipt. ✅"),
    (["officer", "admin", "role", "roles", "staff"],
     "There are 4 roles in UniFind AI:\n• **Student** — report lost items, browse, claim items.\n• **Finder** — register found items they've picked up.\n• **Officer** — review items & claims, complete handovers, manage everything.\n• **Admin** — full access including user management and analytics."),
    (["verification", "question", "private", "secret"],
     "The **verification question** is set by the finder when registering an item — for example: *'What is the wallpaper on the phone?'*\n\nOnly the true owner should know the answer. Answers are stored as **salted hashes** — never as plain text. You have 3 attempts to answer correctly."),
    (["contact", "phone", "email", "reach", "support", "help"],
     "You can reach us at:\n📞 **Phone:** 0922750429\n✉️ **Email:** deressafufa54@gmail.com\n\nOr use the Contact page on the website."),
    (["notification", "notify", "alert"],
     "UniFind AI sends you in-app notifications for:\n• A new potential match for your lost report\n• Your claim being approved or rejected\n• Your found item being approved or rejected\n• Your handover being ready for collection\n\nCheck the 🔔 bell icon in your dashboard."),
    (["photo", "image", "picture", "upload", "profile"],
     "Photos are displayed prominently in the item's profile and improve matching significantly!\n\n**Tips for a good photo:**\n• Good lighting, clear focus\n• Show the entire item\n• Include distinguishing marks or logos\n• Supported formats: JPG, PNG, WEBP (up to 4 photos per item)."),
    (["recovery rate", "statistics", "stats", "how many"],
     "Live statistics are shown on the homepage — including items awaiting owners, lost reports, items returned, and the overall recovery rate. The goal is to maximise that recovery rate! 🎯"),
    (["what is unifind", "about", "what does", "explain the system", "how does it work"],
     "**UniFind AI** is a university lost-and-found platform that uses AI to match lost reports with found items.\n\nHow it works in 4 steps:\n1. **Report** — describe what you lost or found, with a photo.\n2. **Match** — the AI engine ranks possible pairs and explains why.\n3. **Verify** — claimants answer private questions; officers review evidence.\n4. **Return** — a unique handover code and receipt complete the recovery."),
    (["duplicate", "already reported", "same item"],
     "The system automatically detects very similar reports using TF-IDF text similarity. If a duplicate is detected you can either review your entry or confirm it's different and submit anyway."),
    (["archive", "archived", "old item", "retention"],
     "Administrators can archive items after the university's retention period. Archived items are no longer shown publicly but remain in the audit trail for accountability."),
    (["audit", "log", "history", "trail"],
     "Every action in UniFind AI is recorded in an audit trail — item registrations, approvals, rejections, claims, handovers. Admins and officers can review the full timeline of any item."),
    (["thank", "thanks", "great", "awesome", "perfect", "helpful"],
     "You're welcome! 😊 Let me know if there's anything else I can help with."),
    (["bye", "goodbye", "see you", "exit"],
     "Goodbye! I hope UniFind AI helps you get your item back. Good luck! 👋"),
]


def _fallback_chat(user_text: str) -> str:
    """Rule-based answer when Gemini is not available."""
    t = (user_text or "").lower()
    for keywords, answer in _FALLBACK_KB:
        if any(kw in t for kw in keywords):
            return answer
    return (
        "I'm here to help with UniFind AI! You can ask me about:\n"
        "• How to **report a lost item**\n"
        "• How to **register a found item**\n"
        "• How **AI matching** works\n"
        "• How to **claim** an item\n"
        "• **Handover** and collection process\n"
        "• **Direct contact:** 0922750429 / deressafufa54@gmail.com\n\n"
        "What would you like to know? 😊"
    )


def _gemini(contents, system_instruction=None):
    """Call Gemini Flash; returns (text, error). Returns (None, None) if no key configured."""
    if not GEMINI_API_KEY:
        return None, None
    body = {"contents": contents}
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        GEMINI_URL.format(key=GEMINI_API_KEY),
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read())
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return text, None
    except urllib.error.HTTPError as e:
        body_err = e.read().decode(errors="replace")
        return None, f"Gemini API error {e.code}: {body_err[:300]}"
    except Exception as exc:
        return None, str(exc)


# ─── 1. Chat assistant ────────────────────────────────────────────────────────

@bp.post("/chat")
@rate_limit("ai_chat", 60, 60)
def chat():
    p = request.get_json(silent=True) or {}
    messages = p.get("messages", [])
    if not messages or not isinstance(messages, list):
        return error("Provide a messages array.", 422)

    last_user_msg = next((m.get("text", "") for m in reversed(messages) if m.get("role") == "user"), "")

    if GEMINI_API_KEY:
        contents = [
            {"role": m["role"], "parts": [{"text": m["text"]}]}
            for m in messages[-20:]
            if m.get("role") in ("user", "model") and m.get("text")
        ]
        text, err = _gemini(contents, system_instruction=SYSTEM_CONTEXT)
        if text:
            return jsonify({"reply": text})

    # Built-in smart fallback if no API key or Gemini request failed
    reply = _fallback_chat(last_user_msg)
    return jsonify({"reply": reply})


# ─── 2. Image analysis ───────────────────────────────────────────────────────

def _local_image_dominant_color(b64_data):
    """Estimate dominant color from base64 image without external API."""
    try:
        raw = base64.b64decode(b64_data)
        im = Image.open(io.BytesIO(raw)).convert("RGB").resize((50, 50))
        # Simple color classification
        colors = im.getcolors(50 * 50)
        if not colors:
            return "Black"
        dominant = max(colors, key=lambda item: item[0])[1]
        r, g, b = dominant
        if r < 50 and g < 50 and b < 50:
            return "Black"
        if r > 200 and g > 200 and b > 200:
            return "White"
        if abs(r - g) < 20 and abs(g - b) < 20:
            return "Grey"
        if r > g and r > b:
            return "Red" if r > 150 else "Brown"
        if b > r and b > g:
            return "Blue"
        if g > r and g > b:
            return "Green"
        if r > 150 and g > 150 and b < 100:
            return "Yellow"
        return "Grey"
    except Exception:
        return "Black"


@bp.post("/analyze-image")
@rate_limit("ai_image", 20, 60)
def analyze_image():
    """Accept a base64-encoded image and return structured item details."""
    p = request.get_json(silent=True) or {}
    image_b64 = p.get("image_base64", "")
    mime_type = p.get("mime_type", "image/jpeg")
    if not image_b64:
        return error("Provide image_base64.", 422)

    cats = [c.name for c in Category.query.filter_by(is_active=True).all()]
    cat_hint = ", ".join(cats) if cats else "Electronics, Clothing, Bags, Keys, Documents, Other"

    if GEMINI_API_KEY:
        prompt = f"""Analyse this image of a lost or found item.
Return ONLY valid JSON (no markdown, no explanation) with these exact keys:
{{
  "title": "short descriptive title (max 10 words)",
  "category": "best matching category from: {cat_hint}",
  "color": "dominant colour (single word or short phrase)",
  "brand": "brand name if visible, else empty string",
  "description": "2-3 sentence public description suitable for a lost-and-found listing"
}}"""

        contents = [
            {
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": image_b64}},
                    {"text": prompt},
                ],
            }
        ]
        text, _ = _gemini(contents)
        if text:
            cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            try:
                details = json.loads(cleaned)
                for cat in Category.query.filter_by(is_active=True).all():
                    if cat.name.lower() == details.get("category", "").lower():
                        details["category_id"] = cat.id
                        break
                return jsonify({"details": details})
            except Exception:
                pass

    # Local fallback image analysis
    est_color = _local_image_dominant_color(image_b64)
    first_cat = Category.query.filter_by(is_active=True).first()
    fallback_details = {
        "title": f"{est_color} item",
        "category": first_cat.name if first_cat else "Other",
        "category_id": first_cat.id if first_cat else None,
        "color": est_color,
        "brand": "",
        "description": f"Item uploaded with photo. Detected primary color: {est_color}.",
    }
    return jsonify({"details": fallback_details})


# ─── 3. Natural-language search ──────────────────────────────────────────────

@bp.post("/search")
@rate_limit("ai_search", 30, 60)
def nl_search():
    """Parse a natural-language query into structured search filters."""
    p = request.get_json(silent=True) or {}
    query = (p.get("query") or "").strip()
    if not query:
        return error("Provide a query.", 422)

    cats = [c.name for c in Category.query.filter_by(is_active=True).all()]
    locs = [l.name for l in Location.query.filter_by(is_active=True).all()]

    if GEMINI_API_KEY:
        prompt = f"""The user is searching a university lost-and-found system.
User query: "{query}"

Available categories: {', '.join(cats)}
Available locations: {', '.join(locs)}

Return ONLY valid JSON (no markdown) with these keys (use empty string or null for unknown):
{{
  "q": "keyword search string (most important words only)",
  "category": "exact category name from the list or empty string",
  "color": "colour keyword or empty string",
  "location": "exact location name from the list or empty string",
  "date_from": "YYYY-MM-DD or null",
  "date_to": "YYYY-MM-DD or null",
  "summary": "one sentence explaining what the user is looking for"
}}"""

        text, _ = _gemini([{"role": "user", "parts": [{"text": prompt}]}])
        if text:
            cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            try:
                filters = json.loads(cleaned)
                for cat in Category.query.filter_by(is_active=True).all():
                    if cat.name.lower() == filters.get("category", "").lower():
                        filters["category_id"] = cat.id
                        break
                for loc in Location.query.filter_by(is_active=True).all():
                    if loc.name.lower() == filters.get("location", "").lower():
                        filters["location_id"] = loc.id
                        break
                return jsonify({"filters": filters})
            except Exception:
                pass

    # Local fallback parser: match words against DB categories, locations & colors
    q_lower = query.lower()
    matched_cat = next((c for c in Category.query.filter_by(is_active=True).all() if c.name.lower() in q_lower), None)
    matched_loc = next((l for l in Location.query.filter_by(is_active=True).all() if l.name.lower() in q_lower), None)
    colors = ["black", "blue", "red", "green", "white", "grey", "gray", "silver", "brown", "yellow", "navy", "pink", "purple"]
    matched_color = next((c for c in colors if re.search(r"\b" + c + r"\b", q_lower)), "")

    # Clean query keywords
    stop_words = {"i", "lost", "my", "found", "a", "an", "the", "in", "at", "near", "on", "yesterday", "today", "week", "looking", "for"}
    keywords = [w for w in re.findall(r"[a-zA-Z0-9]+", q_lower) if w not in stop_words]

    fallback_filters = {
        "q": " ".join(keywords[:4]),
        "category": matched_cat.name if matched_cat else "",
        "category_id": matched_cat.id if matched_cat else None,
        "location": matched_loc.name if matched_loc else "",
        "location_id": matched_loc.id if matched_loc else None,
        "color": matched_color,
        "date_from": None,
        "date_to": None,
        "summary": f"Searching for {matched_color + ' ' if matched_color else ''}{matched_cat.name if matched_cat else 'items'}"
                   + (f" near {matched_loc.name}" if matched_loc else ""),
    }
    return jsonify({"filters": fallback_filters})


# ─── 4. Richer match explanation ─────────────────────────────────────────────

@bp.post("/explain-match")
@rate_limit("ai_explain", 30, 60)
def explain_match():
    """Generate a friendly AI explanation for a match result."""
    p = request.get_json(silent=True) or {}
    match_id = p.get("match_id")
    if not match_id:
        return error("Provide match_id.", 422)

    row = db.session.get(MatchingResult, match_id)
    if not row:
        return error("Match not found.", 404)

    lost = row.lost_report
    found = row.found_item
    bd = row.breakdown or {}

    if GEMINI_API_KEY:
        prompt = f"""You are explaining a lost-and-found AI match to a university student.

Lost item: "{lost.title}" — {lost.description[:200]}
  Category: {lost.category.name}, Colour: {lost.color or 'unknown'}, Brand: {lost.brand or 'unknown'}, Location: {lost.location.name}

Found item: "{found.title}" — {found.public_description[:200]}
  Category: {found.category.name}, Colour: {found.color or 'unknown'}, Brand: {found.brand or 'unknown'}, Location: {found.location.name}

Match score: {row.score:.0f}/100
Score breakdown:
{json.dumps({k: v for k, v in bd.items() if v and v.get('value') is not None}, indent=2)}

Write a friendly 2-3 sentence explanation of WHY this might be a match. Be honest about uncertainty.
Do NOT repeat the score number. Speak directly to the student ("Your lost item...").
"""
        text, _ = _gemini([{"role": "user", "parts": [{"text": prompt}]}])
        if text:
            return jsonify({"explanation": text.strip()})

    # Local fallback explanation based on signals
    points = []
    if lost.category_id == found.category_id:
        points.append(f"both items belong to the '{lost.category.name}' category")
    if lost.color and found.color and (lost.color.lower() in found.color.lower() or found.color.lower() in lost.color.lower()):
        points.append(f"both share the colour {found.color}")
    if lost.brand and found.brand and lost.brand.lower() == found.brand.lower():
        points.append(f"the brand '{found.brand}' matches")
    if lost.location_id == found.location_id:
        points.append(f"the item was found in the same location ({found.location.name})")

    if points:
        explanation = f"This looks like a strong candidate because {', and '.join(points)}. Check the photos and details carefully, and submit a claim if it matches your property."
    else:
        explanation = f"This item shares description and visual characteristics with your report '{lost.title}'. You can review the public photo and start a claim if it is yours."

    return jsonify({"explanation": explanation})
