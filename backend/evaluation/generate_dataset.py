"""Generate the SYNTHETIC labelled evaluation dataset (deterministic, seed 42).
Run:  python evaluation/generate_dataset.py
Ground truth is known by construction: each lost report has exactly one true found item, paraphrased
differently (synonyms, omitted details). Hard negatives share type/colour with true items."""
import json
import os
import random
from datetime import date, timedelta

random.seed(42)
LOCS = [(1, "Main Library", "Central", 0, 0), (2, "Cafeteria", "Central", 120, 60), (3, "Engineering Building", "North", 50, 400),
        (4, "Science Block", "North", 150, 450), (5, "Dormitory A", "East", 700, 100), (6, "Dormitory B", "East", 760, 160),
        (7, "Sports Field", "South", 300, -500), (8, "Main Gate", "West", -600, 0), (9, "Lecture Hall 1", "Central", -40, 80),
        (10, "Student Clinic", "East", 500, -100)]
TYPES = {  # category_id: (found nouns, lost nouns, brands, features[(found wording, lost wording)])
    1: (["smartphone", "mobile phone"], ["phone", "cellphone"], ["Samsung", "Tecno", "Infinix", "Huawei", "Xiaomi", "iPhone"],
        [("cracked screen", "broken display"), ("with transparent case", "clear cover"), ("lion sticker on the back", "sticker of a lion"), ("pop socket attached", "ring holder on the back")]),
    2: (["laptop", "notebook computer"], ["laptop", "computer"], ["HP", "Dell", "Lenovo", "Acer", "Asus"],
        [("stickers on the lid", "decorated with stickers"), ("scratch on the corner", "scratched edge"), ("with charger", "and its charger"), ("black sleeve", "in a dark pouch")]),
    3: (["leather wallet", "purse"], ["wallet", "purse"], ["Fossil", "Levi's", "Polo", ""],
        [("contains cards", "has bank cards inside"), ("zipper coin pocket", "coin compartment with zip"), ("worn edges", "old and worn")]),
    4: (["set of keys", "key bunch"], ["keys", "bunch of keys"], [""],
        [("three keys on a ring", "3 keys on a ring"), ("football keychain", "soccer keyring"), ("car remote attached", "with a car key fob"), ("red tag", "red label")]),
    5: (["backpack", "rucksack"], ["bag", "backpack"], ["Nike", "Adidas", "Puma", "Jansport", ""],
        [("two front pockets", "2 pockets in front"), ("torn strap", "broken shoulder strap"), ("name tag inside", "has a label inside"), ("keychain on zipper", "keyring on the zip")]),
    6: (["student ID card", "identity card"], ["ID card", "student card"], [""],
        [("in a plastic holder", "inside a plastic cover"), ("with lanyard", "attached to a lanyard"), ("faded photo", "photo is faded")]),
    7: (["wireless earbuds", "headphones"], ["earphones", "headphones"], ["JBL", "Sony", "Oraimo", "Anker", "Beats"],
        [("charging case", "and the case"), ("one earbud missing", "only one piece"), ("over-ear padded", "big ear cups")]),
    8: (["jacket", "hooded sweatshirt"], ["jacket", "hoodie"], ["Nike", "Zara", "H&M", ""],
        [("zip pockets", "pockets with zippers"), ("small stain on sleeve", "a mark on the arm"), ("fleece lining", "warm fur inside")]),
    9: (["textbook", "reference book"], ["book", "textbook"], [""],
        [("highlighted pages", "marked with highlighter"), ("name written inside cover", "owner name on first page"), ("worn spine", "damaged back")]),
    10: (["water bottle", "flask"], ["bottle", "flask"], ["Hydro Flask", "Contigo", ""],
         [("dent near bottom", "bent at the base"), ("sticker of a mountain", "mountain decal"), ("metal lid", "steel cap")]),
}
COLORS = [("black", "black"), ("white", "white"), ("blue", "blue"), ("navy", "dark blue"), ("red", "red"), ("maroon", "dark red"),
          ("green", "green"), ("grey", "gray"), ("silver", "silver"), ("brown", "brown"), ("yellow", "yellow"), ("purple", "purple")]


def make_found(fid, cat, color, brand, feat, loc, dt):
    nouns = TYPES[cat][0]
    noun = random.choice(nouns)
    title = f"{color.capitalize()} {noun}"
    desc = f"{color.capitalize()} {noun}" + (f" by {brand}" if brand else "") + f", {feat[0]}."
    return dict(id=fid, category_id=cat, title=title, description=desc, features=None, color=color, brand=brand or None,
                location_id=loc, date=dt.isoformat())


def make_lost(lid, cat, color_lost, brand, feat, loc, dt):
    noun = random.choice(TYPES[cat][1])
    keep_brand = brand and random.random() < 0.8
    keep_color = random.random() < 0.9
    keep_feat = random.random() < 0.85
    title = f"Lost {noun}"
    desc = "I lost my " + (f"{color_lost} " if keep_color else "") + noun + (f" ({brand})" if keep_brand else "") + \
           (f", {feat[1]}" if keep_feat else "") + ". Please help me find it."
    return dict(id=lid, category_id=cat, title=title, description=desc, features=None,
                color=color_lost if keep_color else None, brand=brand if keep_brand else None, location_id=loc, date=dt.isoformat())


founds, losts, truth = [], [], {}
fid = 1
for lid in range(1, 61):
    cat = random.choice(list(TYPES))
    cf, cl = random.choice(COLORS)
    brand = random.choice(TYPES[cat][2])
    feat = random.choice(TYPES[cat][3])
    lost_loc = random.randint(1, 10)
    found_loc = lost_loc if random.random() < 0.6 else random.choice([l[0] for l in LOCS if l[0] != lost_loc])
    d0 = date(2026, 1, 5) + timedelta(days=random.randint(0, 200))
    d1 = d0 + timedelta(days=random.randint(0, 6))
    founds.append(make_found(fid, cat, cf, brand, feat, found_loc, d1))
    losts.append(make_lost(lid, cat, cl, brand, feat, lost_loc, d0))
    truth[lid] = fid
    fid += 1
# hard negatives: same type (+often same colour) as a true item, different brand/features/place/date
for _ in range(25):
    base = random.choice(founds[:60])
    cat = base["category_id"]
    cf = base["color"] if random.random() < 0.6 else random.choice(COLORS)[0]
    brand = random.choice(TYPES[cat][2])
    founds.append(make_found(fid, cat, cf, brand, random.choice(TYPES[cat][3]), random.randint(1, 10),
                             date(2026, 1, 5) + timedelta(days=random.randint(0, 200))))
    fid += 1
# random distractors
for _ in range(25):
    cat = random.choice(list(TYPES))
    founds.append(make_found(fid, cat, random.choice(COLORS)[0], random.choice(TYPES[cat][2]), random.choice(TYPES[cat][3]),
                             random.randint(1, 10), date(2026, 1, 5) + timedelta(days=random.randint(0, 200))))
    fid += 1

out = {"meta": {"name": "UniFind synthetic matching benchmark v1", "synthetic": True, "seed": 42,
                "lost_reports": len(losts), "found_items": len(founds), "true_pairs": len(truth),
                "description": "Auto-generated paraphrased lost/found pairs with hard negatives. Not real data."},
       "locations": [dict(id=i, name=n, zone=z, x=x, y=y) for i, n, z, x, y in LOCS],
       "losts": losts, "founds": founds, "truth": {str(k): v for k, v in truth.items()}}
path = os.path.join(os.path.dirname(__file__), "dataset.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1)
print("wrote", path, out["meta"])
