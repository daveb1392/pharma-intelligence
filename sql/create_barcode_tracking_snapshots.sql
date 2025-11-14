-- Daily snapshots table for barcode tracking campaign
-- Captures price data every day, even if unchanged (unlike price_history which only logs changes)

CREATE TABLE IF NOT EXISTS barcode_tracking_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Product identification
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    pharmacy_source TEXT NOT NULL,
    site_code TEXT,
    barcode TEXT NOT NULL,
    product_name TEXT,
    brand TEXT,
    product_url TEXT,

    -- Pricing data (snapshot)
    current_price NUMERIC,
    original_price NUMERIC,
    discount_percentage NUMERIC,
    discount_amount NUMERIC,
    bank_discount_price NUMERIC,
    bank_discount_bank TEXT,

    -- Product availability
    in_stock BOOLEAN,
    requires_prescription BOOLEAN,

    -- Snapshot metadata
    scraped_at TIMESTAMPTZ NOT NULL,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- Ensure one snapshot per product per day per pharmacy
    CONSTRAINT barcode_tracking_snapshots_unique
        UNIQUE (pharmacy_source, barcode, snapshot_date)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_barcode_snapshots_barcode
    ON barcode_tracking_snapshots(barcode);

CREATE INDEX IF NOT EXISTS idx_barcode_snapshots_pharmacy
    ON barcode_tracking_snapshots(pharmacy_source);

CREATE INDEX IF NOT EXISTS idx_barcode_snapshots_date
    ON barcode_tracking_snapshots(snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_barcode_snapshots_product_id
    ON barcode_tracking_snapshots(product_id);

-- Composite index for common queries (product over time)
CREATE INDEX IF NOT EXISTS idx_barcode_snapshots_barcode_date
    ON barcode_tracking_snapshots(barcode, snapshot_date DESC);

COMMENT ON TABLE barcode_tracking_snapshots IS
    'Daily price snapshots for targeted barcode tracking campaigns.
     Unlike price_history (which only logs changes), this captures
     daily data even when prices are unchanged.';
