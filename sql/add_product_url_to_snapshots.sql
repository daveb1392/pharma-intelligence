-- Add product_url column to existing barcode_tracking_snapshots table
-- Safe to run multiple times (IF NOT EXISTS)

ALTER TABLE barcode_tracking_snapshots
ADD COLUMN IF NOT EXISTS product_url TEXT;
