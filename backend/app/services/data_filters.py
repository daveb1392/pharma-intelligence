"""Consumer-facing data filters.

Hides stale and visually broken product rows from public API responses
without modifying the underlying scraper data.
"""

from datetime import datetime, timedelta, timezone
from typing import Iterable

FRESHNESS_DAYS = 14


def freshness_cutoff_iso() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=FRESHNESS_DAYS)).isoformat()


def apply_freshness(query):
    return query.gte("scraped_at", freshness_cutoff_iso())


_PLACEHOLDER_FILENAMES = ("logo", "placeholder", "no-image", "noimage", "default")


def _is_placeholder_image(url: str | None) -> bool:
    if not url:
        return False
    filename = url.rsplit("/", 1)[-1].lower()
    stem = filename.rsplit(".", 1)[0]
    return stem in _PLACEHOLDER_FILENAMES or any(
        stem.startswith(p + "-") or stem.startswith(p + "_") for p in _PLACEHOLDER_FILENAMES
    )


def clean_product(product: dict) -> dict:
    if _is_placeholder_image(product.get("image_url")):
        product = {**product, "image_url": None, "image_urls": []}
    return product


def clean_products(products: Iterable[dict]) -> list[dict]:
    return [clean_product(p) for p in products]
