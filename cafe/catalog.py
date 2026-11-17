"""Shared publication validation for full editor, quick edit and bulk actions."""

from pathlib import Path
from flask import current_app
from .db import db


def publication_issues(product):
    issues = []
    if not product["name"].strip():
        issues.append("Name required")
    if not product["description"].strip():
        issues.append("Description required")
    image = product["image"]
    media = (
        db().execute("SELECT 1 FROM media WHERE filename=?", (image,)).fetchone()
        if image
        else None
    )
    if (
        not media
        or not (Path(current_app.config["DATA_DIR"]) / "uploads" / image).is_file()
    ):
        issues.append("Real product image required")
    if (
        not product["category_id"]
        or not db()
        .execute(
            "SELECT 1 FROM categories WHERE id=? AND active=1",
            (product["category_id"],),
        )
        .fetchone()
    ):
        issues.append("Active category required")
    variants = (
        db()
        .execute(
            "SELECT * FROM variants WHERE product_id=? AND active=1", (product["id"],)
        )
        .fetchall()
        if product.get("id")
        else []
    )
    if not variants:
        issues.append("Enable at least one priced variant")
    elif any(v["price"] is None for v in variants):
        issues.append("Price required for every enabled variant")
    if (
        product.get("id")
        and db()
        .execute(
            "SELECT 1 FROM addons WHERE product_id=? AND active=1 AND price_pending=1",
            (product["id"],),
        )
        .fetchone()
    ):
        issues.append("Review enabled extra prices")
    return issues


def validate_publication(product):
    issues = publication_issues(dict(product))
    if issues:
        raise ValueError(
            "Cannot publish: "
            + "; ".join(issues)
            + ". Save as a draft while preparing this product."
        )
