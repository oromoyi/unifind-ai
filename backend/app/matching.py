"""Explainable matching engine.

Signals (each scored 0..1, combined with configurable weights, reported 0..100):
  category     exact category match
  description  TF-IDF (1-2 grams) cosine similarity of title + description + features
  attributes   colour (synonym families) and brand agreement
  location     same place > distance on campus grid (exp. decay) > same zone
  date         found on/after lost date, exponential decay over ~2 weeks
  image        OPTIONAL. Colour-histogram intersection between photos (implemented, simple,
               no deep learning). EXTENSION POINT: replace `ImageEmbedder` with a pretrained
               CNN (e.g. ResNet/CLIP embeddings + cosine) - see docs/IMAGE_MATCHING.md.

A signal that cannot be computed (e.g. no photos) is excluded and the remaining weights are
re-normalised, so missing data never counts as a mismatch. The engine only SUGGESTS matches;
it never establishes ownership or releases an item.
"""
import math
import re
from datetime import date

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import settings_store
from .extensions import db
from .models import FoundItem, Location, LostReport, MatchingResult, utcnow
from .utils import local_image_paths, notify

COLOR_FAMILIES = {
    "black": "black", "white": "white", "grey": "grey", "gray": "grey", "silver": "grey", "ash": "grey",
    "red": "red", "maroon": "red", "burgundy": "red", "crimson": "red",
    "blue": "blue", "navy": "blue", "azure": "blue", "cyan": "blue", "turquoise": "blue",
    "green": "green", "olive": "green", "lime": "green", "teal": "green",
    "yellow": "yellow", "gold": "yellow", "golden": "yellow", "orange": "orange",
    "brown": "brown", "tan": "brown", "beige": "brown", "khaki": "brown", "cream": "brown",
    "pink": "pink", "purple": "purple", "violet": "purple", "lavender": "purple",
}
LABELS = {"category": "Category", "description": "Description", "attributes": "Colour / brand",
          "location": "Location", "date": "Date", "image": "Photo"}


# ---------- signal helpers ----------
def _families(text):
    return {COLOR_FAMILIES[w] for w in re.findall(r"[a-z]+", (text or "").lower()) if w in COLOR_FAMILIES}


def color_score(a, b):
    fa, fb = _families(a), _families(b)
    if not fa or not fb:
        return None
    if (a or "").strip().lower() == (b or "").strip().lower():
        return 1.0
    return 0.85 if fa & fb else 0.0


def brand_score(a, b):
    a, b = (a or "").strip().lower(), (b or "").strip().lower()
    if not a or not b:
        return None
    return 1.0 if (a == b or a in b or b in a) else 0.0


def attributes_score(lost, found):
    parts = [s for s in (color_score(lost.get("color"), found.get("color")),
                         brand_score(lost.get("brand"), found.get("brand"))) if s is not None]
    return sum(parts) / len(parts) if parts else None


def location_score(la, lb):
    if la is None or lb is None:
        return None
    if la["id"] == lb["id"]:
        return 1.0
    if None not in (la.get("x"), la.get("y"), lb.get("x"), lb.get("y")):
        dist = math.hypot(la["x"] - lb["x"], la["y"] - lb["y"])
        return round(0.85 * math.exp(-dist / 300.0), 4)
    return 0.6 if la.get("zone") and la.get("zone") == lb.get("zone") else 0.1


def date_score(lost_date, found_date):
    if not lost_date or not found_date:
        return None
    d = (found_date - lost_date).days
    if d < -1:  # found before it was lost: implausible
        return 0.0
    return math.exp(-max(d, 0) / 14.0)


class ImageEmbedder:
    """Default (dependency-light) embedder: normalised RGB colour histogram.
    Subclass / replace `embed` with a CNN embedding for stronger visual matching."""
    BINS = 8

    def embed(self, path):
        from PIL import Image
        try:
            with Image.open(path) as im:
                im = im.convert("RGB").resize((64, 64))
                hist = im.histogram()
        except Exception:
            return None
        vec = []
        for ch in range(3):
            chan = hist[ch * 256:(ch + 1) * 256]
            step = 256 // self.BINS
            vec += [sum(chan[i:i + step]) for i in range(0, 256, step)]
        total = float(sum(vec)) or 1.0
        return [v / total for v in vec]

    def similarity(self, a, b):
        return sum(min(x, y) for x, y in zip(a, b)) / 3.0  # histogram intersection, 0..1


EMBEDDER = ImageEmbedder()


def image_score(paths_a, paths_b):
    if not paths_a or not paths_b:
        return None
    ea = [e for e in (EMBEDDER.embed(p) for p in paths_a) if e]
    eb = [e for e in (EMBEDDER.embed(p) for p in paths_b) if e]
    if not ea or not eb:
        return None
    return max(EMBEDDER.similarity(x, y) for x in ea for y in eb)


# ---------- explanation ----------
def explain(raw):
    parts = []
    if raw.get("category") == 1:
        parts.append("same category")
    d = raw.get("description")
    if d is not None and d >= 0.45:
        parts.append("similar description")
    elif d is not None and d >= 0.2:
        parts.append("some shared description keywords")
    a = raw.get("attributes")
    if a is not None and a >= 0.85:
        parts.append("matching colour/brand")
    elif a is not None and a >= 0.4:
        parts.append("partly matching colour/brand")
    l = raw.get("location")
    if l is not None and l >= 0.99:
        parts.append("same location")
    elif l is not None and l >= 0.5:
        parts.append("nearby location")
    t = raw.get("date")
    if t is not None and t >= 0.6:
        parts.append("found shortly after it was lost")
    i = raw.get("image")
    if i is not None and i >= 0.7:
        parts.append("visually similar photo (colour histogram)")
    if not parts:
        return "Weak match: few shared characteristics."
    return (parts[0].capitalize() + "".join(", " + p for p in parts[1:-1]) +
            (", and " + parts[-1] if len(parts) > 1 else "") + ".")


# ---------- core ----------
def _text(d):
    return " ".join(filter(None, [d.get("title"), d.get("description"), d.get("features"), d.get("brand"), d.get("color")]))


def compute_pairs(losts, founds, weights, locations, use_images=False):
    """Score every (lost, found) pair. Pure function over plain dicts (used by API and evaluation).

    lost/found dict keys: id, category_id, title, description, features, color, brand,
    location_id, date, image_paths. `locations`: {id: {id,x,y,zone}}.
    Returns {(lost_id, found_id): {"score": 0..100, "breakdown": {...}, "explanation": str}}
    """
    if not losts or not founds:
        return {}
    texts = [_text(d) for d in losts] + [_text(d) for d in founds]
    try:
        tf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit_transform(texts)
        sims = cosine_similarity(tf[:len(losts)], tf[len(losts):])
    except ValueError:  # empty vocabulary
        sims = [[0.0] * len(founds) for _ in losts]
    wsum_all = sum(weights.values()) or 1.0
    out = {}
    for i, lo in enumerate(losts):
        for j, fo in enumerate(founds):
            raw = {
                "category": 1.0 if lo["category_id"] == fo["category_id"] else 0.0,
                "description": float(sims[i][j]),
                "attributes": attributes_score(lo, fo),
                "location": location_score(locations.get(lo["location_id"]), locations.get(fo["location_id"])),
                "date": date_score(lo.get("date"), fo.get("date")),
                "image": image_score(lo.get("image_paths"), fo.get("image_paths")) if use_images else None,
            }
            avail = {k: v for k, v in raw.items() if v is not None and weights.get(k, 0) > 0}
            wsum = sum(weights[k] for k in avail) or wsum_all
            score = 100.0 * sum(weights[k] * v for k, v in avail.items()) / wsum
            breakdown = {k: {"label": LABELS[k], "value": None if raw[k] is None else round(raw[k], 3),
                             "weight": round(weights.get(k, 0) / wsum, 3) if k in avail else 0.0,
                             "points": round(100.0 * weights[k] * raw[k] / wsum, 1) if k in avail else 0.0}
                         for k in raw}
            out[(lo["id"], fo["id"])] = {"score": round(score, 1), "breakdown": breakdown,
                                         "explanation": explain(raw)}
    return out


# ---------- ORM bridge ----------
def _location_map():
    return {l.id: {"id": l.id, "x": l.x, "y": l.y, "zone": l.zone} for l in Location.query.all()}


def lost_dict(r):
    return {"id": r.id, "category_id": r.category_id, "title": r.title, "description": r.description,
            "features": r.distinguishing_features, "color": r.color, "brand": r.brand,
            "location_id": r.location_id, "date": r.lost_date, "image_paths": local_image_paths(r.images)}


def found_dict(f):
    return {"id": f.id, "category_id": f.category_id, "title": f.title, "description": f.public_description,
            "features": None, "color": f.color, "brand": f.brand, "location_id": f.location_id,
            "date": f.found_date, "image_paths": local_image_paths(f.images)}


def _store(results, min_score, notify_score, notify_target):
    """Upsert MatchingResult rows; notify on first time a pair reaches the notify threshold."""
    for (lid, fid), res in results.items():
        row = MatchingResult.query.filter_by(lost_report_id=lid, found_item_id=fid).first()
        if res["score"] < min_score:
            if row:
                db.session.delete(row)
            continue
        is_new = row is None
        if is_new:
            row = MatchingResult(lost_report_id=lid, found_item_id=fid)
            db.session.add(row)
        row.score, row.breakdown, row.explanation = res["score"], res["breakdown"], res["explanation"]
        row.updated_at = utcnow()
        if is_new and res["score"] >= notify_score:
            owner_id, title = notify_target(lid, fid)
            if owner_id:
                notify(owner_id, "match", "Potential match found",
                       f"{title}: {res['score']:.0f}% match. {res['explanation']}", f"/app/lost/{lid}")


def run_for_lost(report):
    """Match one lost report against all available found items (call inside a request; caller commits)."""
    s = settings_store
    founds = FoundItem.query.filter_by(status="available").all()
    res = compute_pairs([lost_dict(report)], [found_dict(f) for f in founds], s.get("match_weights"),
                        _location_map(), use_images=True)
    _store(res, s.get("match_min_score"), s.get("match_notify_score"), lambda lid, fid: (report.user_id, report.title))
    # drop stale rows for items no longer available
    for row in MatchingResult.query.filter_by(lost_report_id=report.id).all():
        if row.found_item.status != "available":
            db.session.delete(row)
    return res


def run_for_found(item):
    """Match a newly available found item against all open lost reports."""
    s = settings_store
    losts = LostReport.query.filter_by(status="open").all()
    owners = {r.id: (r.user_id, r.title) for r in losts}
    res = compute_pairs([lost_dict(r) for r in losts], [found_dict(item)], s.get("match_weights"),
                        _location_map(), use_images=True)
    _store(res, s.get("match_min_score"), s.get("match_notify_score"), lambda lid, fid: owners[lid])
    return res


def ranked_for_lost(report_id, limit=None):
    limit = limit or settings_store.get("match_max_results")
    rows = (MatchingResult.query.filter_by(lost_report_id=report_id)
            .order_by(MatchingResult.score.desc()).limit(limit * 2).all())
    rows = [r for r in rows if r.found_item.status == "available"][:limit]
    return rows


def match_dict(row):
    return {"id": row.id, "lost_report_id": row.lost_report_id, "score": row.score,
            "explanation": row.explanation, "breakdown": row.breakdown,
            "found_item": row.found_item.to_public()}
