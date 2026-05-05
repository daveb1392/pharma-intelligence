"""Delete farma_center products rows with NULL site_code.

Background:
The unique constraint on products is (pharmacy_source, site_code). Postgres
treats NULL as distinct in unique constraints, so every Phase 2 scrape that
failed to extract a site_code created a new row instead of updating one.
788 such rows accumulated, each carrying a URL from one product but the name
and image extracted from whatever the pharmacy now serves at that site_code
(see e.g. a row whose name is "LERCATEN" but URL points to the "Scentos
boligrafos" slug).

Phase B's scraper fix (URL-pattern fallback in extract_from_html + a guard
that skips upsert when site_code is still None) prevents new zombies. This
script removes the historical ones.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client


def main() -> int:
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("Missing SUPABASE_URL / SUPABASE_KEY in env", file=sys.stderr)
        return 2
    sb = create_client(url, key)

    before = (
        sb.table("products")
        .select("*", count="exact", head=True)
        .eq("pharmacy_source", "farma_center")
        .is_("site_code", "null")
        .execute()
    )
    print(f"farma_center rows with NULL site_code: {before.count}")

    if before.count == 0:
        print("Nothing to delete.")
        return 0

    if "--apply" not in sys.argv:
        print("Re-run with --apply to delete.")
        return 0

    result = (
        sb.table("products")
        .delete()
        .eq("pharmacy_source", "farma_center")
        .is_("site_code", "null")
        .execute()
    )
    print(f"Deleted {len(result.data or [])} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
