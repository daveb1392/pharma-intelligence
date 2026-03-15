-- PrecioFarma Consumer Platform - Database Setup
-- Run this in Supabase SQL Editor

-- ============================================
-- 1. Enable extensions
-- ============================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================
-- 2. Search indexes on products table
-- ============================================

-- Full-text search vector (Spanish dictionary)
ALTER TABLE products ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('spanish',
            coalesce(product_name, '') || ' ' ||
            coalesce(brand, '') || ' ' ||
            coalesce(barcode, '')
        )
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_products_search ON products USING GIN(search_vector);

-- Trigram indexes for typo-tolerant search
CREATE INDEX IF NOT EXISTS idx_products_name_trgm ON products USING GIN(product_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_brand_trgm ON products USING GIN(brand gin_trgm_ops);

-- Barcode lookup (critical for cross-pharmacy comparison)
CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode) WHERE barcode IS NOT NULL;

-- Category browsing
CREATE INDEX IF NOT EXISTS idx_products_category ON products(main_category);

-- Composite for common query pattern
CREATE INDEX IF NOT EXISTS idx_products_barcode_pharmacy ON products(barcode, pharmacy_source);

-- ============================================
-- 3. Search function
-- ============================================

CREATE OR REPLACE FUNCTION search_products(
    search_query TEXT,
    p_limit INT DEFAULT 20,
    p_offset INT DEFAULT 0,
    p_pharmacy TEXT DEFAULT NULL,
    p_category TEXT DEFAULT NULL
) RETURNS JSON AS $$
DECLARE
    result JSON;
    clean_query TEXT;
    fts_count INT;
BEGIN
    clean_query := trim(search_query);

    -- Check if it's a barcode query (pure digits)
    IF clean_query ~ '^\d{8,}$' THEN
        SELECT json_build_object(
            'results', COALESCE((
                SELECT json_agg(row_to_json(t))
                FROM (
                    SELECT
                        p.barcode,
                        p.product_name,
                        p.brand,
                        p.image_url,
                        p.main_category,
                        p.current_price,
                        p.pharmacy_source,
                        p.original_price,
                        p.discount_percentage,
                        p.bank_discount_price,
                        p.bank_discount_bank_name,
                        p.requires_prescription,
                        p.product_url,
                        p.scraped_at
                    FROM products p
                    WHERE p.barcode = clean_query
                        AND (p_pharmacy IS NULL OR p.pharmacy_source = p_pharmacy)
                    ORDER BY p.current_price ASC NULLS LAST
                ) t
            ), '[]'::json),
            'total', (SELECT COUNT(*) FROM products WHERE barcode = clean_query AND (p_pharmacy IS NULL OR pharmacy_source = p_pharmacy))
        ) INTO result;
        RETURN result;
    END IF;

    -- Full-text search with trigram fallback
    WITH fts_results AS (
        SELECT
            p.*,
            ts_rank(p.search_vector, plainto_tsquery('spanish', clean_query)) as rank
        FROM products p
        WHERE p.search_vector @@ plainto_tsquery('spanish', clean_query)
            AND (p_pharmacy IS NULL OR p.pharmacy_source = p_pharmacy)
            AND (p_category IS NULL OR p.main_category = p_category)
    ),
    fuzzy_results AS (
        SELECT
            p.*,
            similarity(p.product_name, clean_query) as rank
        FROM products p
        WHERE similarity(p.product_name, clean_query) > 0.15
            AND (p_pharmacy IS NULL OR p.pharmacy_source = p_pharmacy)
            AND (p_category IS NULL OR p.main_category = p_category)
            AND NOT EXISTS (SELECT 1 FROM fts_results LIMIT 1)
        ORDER BY rank DESC
        LIMIT 200
    ),
    combined AS (
        SELECT * FROM fts_results
        UNION ALL
        SELECT * FROM fuzzy_results
    ),
    -- Group by barcode to show cross-pharmacy results
    grouped AS (
        SELECT DISTINCT ON (COALESCE(c.barcode, c.pharmacy_source || ':' || c.site_code))
            COALESCE(c.barcode, c.pharmacy_source || ':' || c.site_code) as group_key,
            c.barcode,
            c.product_name,
            c.brand,
            c.image_url,
            c.main_category,
            c.requires_prescription,
            c.rank
        FROM combined c
        ORDER BY COALESCE(c.barcode, c.pharmacy_source || ':' || c.site_code), c.rank DESC
    ),
    counted AS (
        SELECT COUNT(*) as total FROM grouped
    ),
    paged AS (
        SELECT g.*,
            (SELECT MIN(p2.current_price) FROM products p2 WHERE p2.barcode = g.barcode AND p2.barcode IS NOT NULL) as best_price,
            (SELECT COUNT(DISTINCT p2.pharmacy_source) FROM products p2 WHERE p2.barcode = g.barcode AND p2.barcode IS NOT NULL) as pharmacy_count
        FROM grouped g
        ORDER BY g.rank DESC
        LIMIT p_limit OFFSET p_offset
    )
    SELECT json_build_object(
        'results', COALESCE((SELECT json_agg(row_to_json(p)) FROM paged p), '[]'::json),
        'total', (SELECT total FROM counted)
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 4. User favorites table
-- ============================================

CREATE TABLE IF NOT EXISTS user_favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    barcode TEXT NOT NULL,
    product_name TEXT,
    brand TEXT,
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, barcode)
);

CREATE INDEX IF NOT EXISTS idx_favorites_user ON user_favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_barcode ON user_favorites(barcode);

-- ============================================
-- 5. User alerts table
-- ============================================

CREATE TABLE IF NOT EXISTS user_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    barcode TEXT NOT NULL,
    product_name TEXT,
    target_price NUMERIC,
    alert_type TEXT NOT NULL DEFAULT 'price_drop',
    is_active BOOLEAN DEFAULT TRUE,
    phone_number TEXT,
    last_notified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, barcode)
);

CREATE INDEX IF NOT EXISTS idx_alerts_user ON user_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_barcode ON user_alerts(barcode);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON user_alerts(is_active) WHERE is_active = TRUE;

-- ============================================
-- 6. Price history table + trigger
-- ============================================

CREATE TABLE IF NOT EXISTS price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    pharmacy_source TEXT NOT NULL,
    site_code TEXT NOT NULL,
    product_name TEXT,
    current_price NUMERIC,
    original_price NUMERIC,
    discount_percentage NUMERIC,
    discount_amount NUMERIC,
    bank_discount_price NUMERIC,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    change_type TEXT,
    CONSTRAINT price_history_unique UNIQUE (product_id, recorded_at)
);

CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_pharmacy_source ON price_history(pharmacy_source);
CREATE INDEX IF NOT EXISTS idx_price_history_recorded_at ON price_history(recorded_at DESC);

-- Trigger function to log price changes automatically
CREATE OR REPLACE FUNCTION log_price_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE') THEN
        IF (
            OLD.current_price IS DISTINCT FROM NEW.current_price OR
            OLD.original_price IS DISTINCT FROM NEW.original_price OR
            OLD.discount_percentage IS DISTINCT FROM NEW.discount_percentage OR
            OLD.discount_amount IS DISTINCT FROM NEW.discount_amount OR
            OLD.bank_discount_price IS DISTINCT FROM NEW.bank_discount_price
        ) THEN
            INSERT INTO price_history (
                product_id, pharmacy_source, site_code, product_name,
                current_price, original_price, discount_percentage,
                discount_amount, bank_discount_price, recorded_at, change_type
            ) VALUES (
                NEW.id, NEW.pharmacy_source, NEW.site_code, NEW.product_name,
                NEW.current_price, NEW.original_price, NEW.discount_percentage,
                NEW.discount_amount, NEW.bank_discount_price, NEW.scraped_at,
                CASE
                    WHEN OLD.current_price < NEW.current_price THEN 'price_increase'
                    WHEN OLD.current_price > NEW.current_price THEN 'price_decrease'
                    WHEN OLD.discount_percentage IS NULL AND NEW.discount_percentage IS NOT NULL THEN 'discount_added'
                    WHEN OLD.discount_percentage IS NOT NULL AND NEW.discount_percentage IS NULL THEN 'discount_removed'
                    ELSE 'price_modified'
                END
            );
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_log_price_change ON products;
CREATE TRIGGER trigger_log_price_change
    AFTER UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION log_price_change();

-- ============================================
-- 7. Row Level Security
-- ============================================

-- Products: public read access
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Products are viewable by everyone" ON products;
CREATE POLICY "Products are viewable by everyone"
    ON products FOR SELECT USING (true);

-- Price history: public read access
ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Price history viewable by everyone" ON price_history;
CREATE POLICY "Price history viewable by everyone"
    ON price_history FOR SELECT USING (true);

-- User favorites: users manage their own
ALTER TABLE user_favorites ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users manage own favorites" ON user_favorites;
CREATE POLICY "Users manage own favorites"
    ON user_favorites FOR ALL USING (auth.uid() = user_id);

-- User alerts: users manage their own
ALTER TABLE user_alerts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users manage own alerts" ON user_alerts;
CREATE POLICY "Users manage own alerts"
    ON user_alerts FOR ALL USING (auth.uid() = user_id);

-- ============================================
-- 8. Categories materialized view
-- ============================================

DROP MATERIALIZED VIEW IF EXISTS categories_mv;
CREATE MATERIALIZED VIEW categories_mv AS
SELECT
    main_category,
    COUNT(*) as product_count,
    COUNT(DISTINCT pharmacy_source) as pharmacy_count,
    MIN(current_price) as min_price,
    MAX(current_price) as max_price
FROM products
WHERE main_category IS NOT NULL AND main_category != ''
GROUP BY main_category
ORDER BY product_count DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_mv ON categories_mv(main_category);

-- Refresh this view daily after scraping:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY categories_mv;
