"""Offline evaluation: baseline keyword search vs. the weighted matcher on a LABELLED dataset.

The bundled dataset (evaluation/dataset.json) is SYNTHETIC (see generate_dataset.py) - results on it
demonstrate the methodology, not real-world performance. Replace it with anonymised, hand-labelled
real pairs for a defensible final evaluation.
"""
import json
import os
import re
from datetime import date

from .matching import compute_pairs

DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "evaluation", "dataset.json")
STOP = set("a an the my i of on in at to and or with near by is was it its this that for from has have had lost found".split())


def load_dataset(path=DATASET_PATH):
    with open(path, encoding="utf-8") as fh:
        ds = json.load(fh)
    for d in ds["losts"] + ds["founds"]:
        d["date"] = date.fromisoformat(d["date"])
        d["image_paths"] = []
    ds["truth"] = {int(k): v for k, v in ds["truth"].items()}
    return ds


def _tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in STOP}


def baseline_scores(losts, founds):
    """Plain keyword search: score = number of query keywords found in title/description/brand/colour."""
    out = {}
    for lo in losts:
        q = _tokens(f"{lo['title']} {lo['description']} {lo.get('features') or ''}")
        for fo in founds:
            d = _tokens(f"{fo['title']} {fo['description']} {fo.get('brand') or ''} {fo.get('color') or ''}")
            out[(lo["id"], fo["id"])] = float(len(q & d))
    return out


def _rank_metrics(scores, losts, founds, truth):
    ranks = []
    for lo in losts:
        ordered = sorted(founds, key=lambda f: (-scores[(lo["id"], f["id"])], f["id"]))
        ids = [f["id"] for f in ordered]
        ranks.append(ids.index(truth[lo["id"]]) + 1)
    n = len(ranks)
    return {"precision_at_1": round(sum(r == 1 for r in ranks) / n, 3),
            "hit_rate_at_3": round(sum(r <= 3 for r in ranks) / n, 3),
            "hit_rate_at_5": round(sum(r <= 5 for r in ranks) / n, 3),
            "mrr": round(sum(1 / r for r in ranks) / n, 3), "queries": n}


def _pr_at_threshold(scores, truth, thr):
    tp = fp = 0
    truth_pairs = {(l, f) for l, f in truth.items()}
    for pair, s in scores.items():
        if s >= thr:
            if pair in truth_pairs:
                tp += 1
            else:
                fp += 1
    fn = len(truth_pairs) - tp
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if truth_pairs else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"threshold": thr, "precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3),
            "true_positives": tp, "false_positives": fp, "false_negatives": fn}


def run_evaluation(weights, thresholds=(30, 40, 50, 60, 70), path=DATASET_PATH):
    ds = load_dataset(path)
    locs = {l["id"]: l for l in ds["locations"]}
    res = compute_pairs(ds["losts"], ds["founds"], weights, locs, use_images=False)
    m_scores = {k: v["score"] for k, v in res.items()}
    b_scores = baseline_scores(ds["losts"], ds["founds"])
    max_b = max(b_scores.values()) or 1.0
    b_norm = {k: 100 * v / max_b for k, v in b_scores.items()}
    return {
        "dataset": ds["meta"],
        "weights": weights,
        "baseline_keyword": _rank_metrics(b_scores, ds["losts"], ds["founds"], ds["truth"]),
        "weighted_matcher": _rank_metrics(m_scores, ds["losts"], ds["founds"], ds["truth"]),
        "threshold_curve": {
            "matcher": [_pr_at_threshold(m_scores, ds["truth"], t) for t in thresholds],
            "baseline_keyword_normalised": [_pr_at_threshold(b_norm, ds["truth"], t) for t in thresholds],
        },
        "note": "Computed on a synthetic labelled dataset; image similarity excluded (no photos). "
                "Do not present these numbers as real-world performance.",
    }
