"""Update demo item images with real high-resolution photographs."""
import os
import urllib.request

from app import create_app
from app.models import FoundItem, LostReport

REAL_PHOTOS = {
    # Laptop / PC
    "laptop": "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80",
    "hp": "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80",
    "pc": "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80",
    # Keys
    "key": "https://images.unsplash.com/photo-1582139329536-e7284fece509?w=600&auto=format&fit=crop&q=80",
    # Phone / Samsung
    "samsung": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=600&auto=format&fit=crop&q=80",
    "phone": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop&q=80",
    # Wallet
    "wallet": "https://images.unsplash.com/photo-1627123424574-724758594e93?w=600&auto=format&fit=crop&q=80",
    # Backpack / Bag
    "backpack": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80",
    "bag": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80",
    # Earbuds / Headphones / Earphones
    "earbuds": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&auto=format&fit=crop&q=80",
    "earphones": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&auto=format&fit=crop&q=80",
    # Clothing / Jacket
    "jacket": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=600&auto=format&fit=crop&q=80",
    "hooded": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=600&auto=format&fit=crop&q=80",
    # Books
    "textbook": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80",
    "calculus": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80",
    # Bottle
    "bottle": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&auto=format&fit=crop&q=80",
    # ID Card
    "id card": "https://images.unsplash.com/photo-1618042164219-62c820f10723?w=600&auto=format&fit=crop&q=80",
    "holder": "https://images.unsplash.com/photo-1618042164219-62c820f10723?w=600&auto=format&fit=crop&q=80",
}


def get_photo_url_for_title(title):
    t = title.lower()
    for kw, url in REAL_PHOTOS.items():
        if kw in t:
            return url
    return "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80"


def update_images():
    app = create_app()
    with app.app_context():
        upload_dir = app.config["UPLOAD_DIR"]
        os.makedirs(upload_dir, exist_ok=True)

        items = list(FoundItem.query.all()) + list(LostReport.query.all())
        updated = 0

        for item in items:
            url = get_photo_url_for_title(item.title)
            for img in item.images:
                dest_path = os.path.join(upload_dir, img.filename)
                try:
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        img_data = resp.read()

                    with open(dest_path, "wb") as f:
                        f.write(img_data)
                    updated += 1
                    print(f"Updated {item.title} -> {img.filename} with real photo")
                except Exception as e:
                    print(f"Failed to update {img.filename} for {item.title}: {e}")

        print(f"Finished! Updated {updated} images with real item photos.")


if __name__ == "__main__":
    update_images()
