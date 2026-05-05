-- Cleanup: delete farma_center rows with NULL site_code (788 zombies).
--
-- Background: the unique constraint on products is (pharmacy_source, site_code).
-- Postgres treats NULL as distinct in unique constraints, so every Phase 2
-- scrape that failed to extract a site_code created a NEW row instead of
-- updating one. 788 zombies accumulated, each carrying a URL from one product
-- but the name/image scraped from whatever the pharmacy now serves at that
-- site_code.
--
-- The scraper is now patched (see scrapers/farmacia_center.py: URL-pattern
-- fallback in extract_from_html + a guard that skips upsert when site_code
-- is still None). This statement removes the historical wreckage.
--
-- Run in the Supabase SQL editor.

BEGIN;

-- Sanity check the scope before deleting
SELECT count(*) AS rows_to_delete
FROM products
WHERE pharmacy_source = 'farma_center'
  AND site_code IS NULL;

DELETE FROM products
WHERE pharmacy_source = 'farma_center'
  AND site_code IS NULL;

-- Verify
SELECT count(*) AS remaining_nulls
FROM products
WHERE pharmacy_source = 'farma_center'
  AND site_code IS NULL;

COMMIT;
