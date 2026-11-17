"""Opt-in sample assets for approved starter products; never replaces owner content."""

import hashlib
from pathlib import Path
from flask import current_app
from .db import db, audit
from .starter_catalog import DRINKS, COFFEE


def starter_descriptions():
    descriptions = {}
    for _, _, items in DRINKS:
        for slug, name, description, size, temperature in items:
            descriptions["starter.v21.product." + slug] = description
    for _, _, slug, name, description, types in COFFEE:
        descriptions["starter.v21.product." + slug] = description
    return descriptions


def sample_source(starter_key):
    descriptions = starter_descriptions()
    if starter_key not in descriptions:
        return None
    slug = starter_key.removeprefix("starter.v21.product.")
    return (
        Path(current_app.static_folder) / "images" / "starter-samples" / (slug + ".jpg")
    )


def prepare_catalog_preview():
    conn = db()
    descriptions = starter_descriptions()
    products = conn.execute(
        "SELECT * FROM products WHERE starter_key LIKE 'starter.v21.product.%' ORDER BY id"
    ).fetchall()
    if not products:
        raise ValueError(
            "Run the starter catalog seed first, then prepare its sample images."
        )
    changes = [
        p
        for p in products
        if p["starter_key"] in descriptions
        and (not p["image"] or not (p["description"] or "").strip())
    ]
    if not changes:
        return dict(images=0, descriptions=0, backup=None)
    from .commands import make_backup

    backup = make_backup()
    created_files = []
    images = filled = 0
    conn.execute("BEGIN IMMEDIATE")
    try:
        # Re-read under the write lock so concurrent owner edits win.
        for old in changes:
            product = conn.execute(
                "SELECT * FROM products WHERE id=?", (old["id"],)
            ).fetchone()
            if not product or product["starter_key"] not in descriptions:
                continue
            if not (product["description"] or "").strip():
                conn.execute(
                    "UPDATE products SET description=? WHERE id=?",
                    (descriptions[product["starter_key"]], product["id"]),
                )
                filled += 1
            if product["image"]:
                continue
            source = sample_source(product["starter_key"])
            content = source.read_bytes()
            digest = hashlib.sha256(content).hexdigest()[:16]
            slug = source.stem
            filename = f"starter-sample-{slug}-{digest}.jpg"
            target = Path(current_app.config["DATA_DIR"]) / "uploads" / filename
            try:
                with target.open("xb") as output:
                    output.write(content)
                created_files.append(target)
            except FileExistsError:
                if target.read_bytes() != content:
                    raise ValueError(
                        "A conflicting sample file exists; no owner file was overwritten."
                    )
            conn.execute(
                "INSERT OR IGNORE INTO media(filename,title,alt) VALUES (?,?,?)",
                (
                    filename,
                    "Sample illustration — " + product["name"],
                    "Sample illustration of "
                    + product["name"]
                    + "; not actual product photography",
                ),
            )
            conn.execute(
                "UPDATE products SET image=? WHERE id=? AND (image='' OR image IS NULL)",
                (filename, product["id"]),
            )
            images += 1
        audit(
            f"Prepared starter sample content: {images} images, {filled} missing descriptions"
        )
        conn.commit()
    except Exception:
        conn.rollback()
        for path in created_files:
            path.unlink(missing_ok=True)
        raise
    return dict(images=images, descriptions=filled, backup=str(backup))
