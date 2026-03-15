-- Add normalized_category column to products table
ALTER TABLE products ADD COLUMN IF NOT EXISTS normalized_category TEXT;

-- Index for fast filtering
CREATE INDEX IF NOT EXISTS idx_products_normalized_category ON products(normalized_category);

-- Refresh the materialized view to use normalized_category
DROP MATERIALIZED VIEW IF EXISTS categories_mv;
CREATE MATERIALIZED VIEW categories_mv AS
SELECT
    normalized_category as main_category,
    COUNT(*) as product_count,
    COUNT(DISTINCT pharmacy_source) as pharmacy_count,
    MIN(current_price) as min_price,
    MAX(current_price) as max_price
FROM products
WHERE normalized_category IS NOT NULL
GROUP BY normalized_category
ORDER BY product_count DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_mv ON categories_mv(main_category);

-- Helper function so the Python script can refresh the view via RPC
CREATE OR REPLACE FUNCTION refresh_categories_mv()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY categories_mv;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- NOTE: After running this one-time migration, just run:
--   python -m scripts.normalize_categories
-- The script handles normalization + view refresh automatically.
