-- Fix: price_history trigger fails under RLS
--
-- Problem: log_price_change() runs as the caller's role. When the scraper
-- writes to `products` with the anon key, the trigger's INSERT into
-- `price_history` is evaluated against the anon role's RLS policies, which
-- only allow SELECT. The whole upsert rolls back with:
--   "new row violates row-level security policy for table price_history"
--
-- Fix: recreate the function with SECURITY DEFINER so it runs as the function
-- owner (postgres) and bypasses RLS for the internal insert. This is the
-- canonical Postgres pattern for data-integrity triggers.
--
-- Apply via Supabase SQL editor (or psql with service role).

CREATE OR REPLACE FUNCTION log_price_change()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
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
$$;
