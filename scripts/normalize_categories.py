"""
Normalize product categories after scraping.

Reads category_path and main_category from products table,
applies normalization rules, writes to normalized_category column,
and refreshes the categories_mv materialized view.

Run after each scraping cycle (single command, handles everything):
    python -m scripts.normalize_categories
"""

import time
from collections import defaultdict

from storage.supabase_loader import SupabaseLoader

# Normalization rules: (match_fn, normalized_name)
# Checked in order — first match wins
RULES = [
    (lambda c: "cardiovascular" in c or "hipertens" in c, "Sistema Cardiovascular"),
    (lambda c: "analg" in c or "antiinflam" in c or "anti-inflam" in c or "dolor" in c, "Analgésicos"),
    (lambda c: "respirat" in c or "expectorant" in c, "Aparato Respiratorio"),
    (lambda c: "nervio" in c or "psiquiat" in c or "ansiolít" in c, "Sistema Nervioso"),
    (lambda c: "antiinfecc" in c or "antibiot" in c or "antifung" in c, "Antiinfecciosos"),
    (lambda c: "genitourin" in c or "ginecol" in c or "urol" in c, "Sistema Genitourinario"),
    (lambda c: "digest" in c or "gastro" in c or "estomac" in c, "Aparato Digestivo"),
    (lambda c: "vitamin" in c or "multivitam" in c, "Vitaminas y Minerales"),
    (lambda c: "suplement" in c or "supl." in c, "Suplementos"),
    (lambda c: "leche" in c or "formula" in c or "fórmula" in c, "Leches y Fórmulas"),
    (lambda c: "deport" in c or "recuper" in c or "proteín" in c or "protein" in c, "Nutrición Deportiva"),
    (lambda c: "diabetes" in c or "insulina" in c, "Diabetes"),
    (lambda c: "oftalmol" in c or "ocular" in c, "Oftalmología"),
    (lambda c: "antihistam" in c or "alerg" in c, "Antihistamínicos"),
    (lambda c: "hospital" in c, "Hospitalarios"),
    (lambda c: "dermatol" in c or "piel" in c or "capilar" in c, "Dermatología"),
    (lambda c: "protecc" in c or "preserv" in c, "Protección"),
    (lambda c: "golosin" in c or "infusi" in c, "Alimentos y Bebidas"),
    (lambda c: "aliment" in c or "bebid" in c or "cereal" in c, "Alimentos y Bebidas"),
    (lambda c: "oncol" in c or "antineopl" in c, "Oncología"),
    (lambda c: "endocrin" in c or "hormon" in c or "tiroides" in c, "Sistema Endocrino"),
    (lambda c: "muscul" in c or "relajant" in c or "osteopor" in c, "Sistema Musculoesquelético"),
    (lambda c: "hemato" in c or "coagul" in c or "anemia" in c, "Hematología"),
]


def normalize(category_path: list | None, main_category: str | None) -> str:
    """Determine normalized category from category_path and main_category."""
    # Try subcategory (level 2) first — most useful granularity
    raw = None
    if category_path and len(category_path) >= 2:
        raw = category_path[1]
    elif main_category:
        raw = main_category

    if not raw:
        return "Sin Categoría"

    # Clean up
    raw_lower = raw.lower().strip().strip(".")

    # Check if main_category itself is just "medicamentos" — not useful, try subcategory
    if raw_lower in ("medicamentos", "...medicamentos"):
        if category_path and len(category_path) >= 2:
            raw = category_path[1]
            raw_lower = raw.lower().strip().strip(".")
        else:
            return "Medicamentos"

    # Apply normalization rules
    for match_fn, normalized in RULES:
        if match_fn(raw_lower):
            return normalized

    # If it's "otros" or generic
    if raw_lower == "otros":
        return "Otros"

    # Return cleaned version of whatever we have
    return raw.strip(".").strip().title()


def run():
    loader = SupabaseLoader()
    batch_size = 1000
    offset = 0
    total_fetched = 0

    # Phase 1a: Fetch all products and compute normalized categories
    print("Phase 1a: Computing normalized categories...")
    category_to_ids: dict[str, list[str]] = defaultdict(list)
    # Track products with no category + barcode for backfill
    uncategorized: list[dict] = []
    # Build barcode → category map from products that have categories
    barcode_category_map: dict[str, str] = {}

    while True:
        result = (
            loader.client.table("products")
            .select("id, barcode, category_path, main_category")
            .range(offset, offset + batch_size - 1)
            .execute()
        )

        if not result.data:
            break

        for product in result.data:
            normalized = normalize(
                product.get("category_path"),
                product.get("main_category"),
            )
            if normalized == "Sin Categoría" and product.get("barcode"):
                uncategorized.append(product)
            else:
                category_to_ids[normalized].append(product["id"])
                # Remember barcode → category for backfill
                if product.get("barcode") and normalized != "Sin Categoría":
                    barcode_category_map[product["barcode"]] = normalized

        total_fetched += len(result.data)
        offset += batch_size
        print(f"  Fetched {total_fetched} products...")

    # Phase 1b: Backfill uncategorized products via barcode matching
    backfilled = 0
    for product in uncategorized:
        matched_cat = barcode_category_map.get(product["barcode"])
        if matched_cat:
            category_to_ids[matched_cat].append(product["id"])
            backfilled += 1
        else:
            category_to_ids["Sin Categoría"].append(product["id"])

    print(f"  Found {len(category_to_ids)} unique categories for {total_fetched} products")
    print(f"  Backfilled {backfilled}/{len(uncategorized)} uncategorized products via barcode matching")

    # Phase 2: Batch update by category (one API call per category group)
    print("\nPhase 2: Updating products by category...")
    total_updated = 0
    chunk_size = 200  # Supabase .in_() limit

    for cat_name, ids in category_to_ids.items():
        # Split into chunks for the .in_() filter
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i : i + chunk_size]
            for attempt in range(3):
                try:
                    loader.client.table("products").update(
                        {"normalized_category": cat_name}
                    ).in_("id", chunk).execute()
                    total_updated += len(chunk)
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                    else:
                        print(f"  Failed batch for '{cat_name}': {e}")

        print(f"  [{total_updated}/{total_fetched}] {cat_name} ({len(ids)} products)")

    print(f"\nDone! Normalized {total_updated} products into {len(category_to_ids)} categories.")

    # Phase 3: Refresh the materialized view via RPC
    print("\nPhase 3: Refreshing categories_mv materialized view...")
    try:
        loader.client.rpc("refresh_categories_mv", {}).execute()
        print("  View refreshed successfully!")
    except Exception as e:
        print(f"  Could not auto-refresh view: {e}")
        print("  Run manually in Supabase SQL Editor:")
        print("    REFRESH MATERIALIZED VIEW CONCURRENTLY categories_mv;")


if __name__ == "__main__":
    run()
