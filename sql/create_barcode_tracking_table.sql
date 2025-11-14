-- Create separate table for barcode tracking URLs
-- This keeps tracking isolated from main product_urls table

CREATE TABLE IF NOT EXISTS barcode_tracking_urls (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pharmacy_source TEXT NOT NULL,
    product_url TEXT NOT NULL,
    site_code TEXT,
    barcode TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure no duplicate URLs per pharmacy
    UNIQUE(pharmacy_source, product_url)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_barcode_tracking_pharmacy
ON barcode_tracking_urls(pharmacy_source);

CREATE INDEX IF NOT EXISTS idx_barcode_tracking_barcode
ON barcode_tracking_urls(barcode);

-- Comments
COMMENT ON TABLE barcode_tracking_urls IS 'Temporary table for tracking specific products by barcode';
COMMENT ON COLUMN barcode_tracking_urls.pharmacy_source IS 'Pharmacy identifier (farma_oliva, punto_farma, etc)';
COMMENT ON COLUMN barcode_tracking_urls.product_url IS 'Product page URL to scrape';
COMMENT ON COLUMN barcode_tracking_urls.site_code IS 'Pharmacy internal product code';
COMMENT ON COLUMN barcode_tracking_urls.barcode IS 'Product barcode (EAN/UPC)';
