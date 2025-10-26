# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Pharma Intelligence** - Multi-pharmacy price comparison platform for a pharmaceutical laboratory client. Scrapes 4 Paraguayan pharmacy websites, performs intelligent product matching using barcodes and AI, and provides competitive analytics via Supabase + BigQuery + dbt + Looker Studio.

## Target Pharmacy Websites

1. Farma Oliva - https://www.farmaoliva.com.py/
2. Punto Farma - https://www.puntofarma.com.py/
3. Farma Center - https://www.farmacenter.com.py/
4. Farmacia Catedral - https://www.farmaciacatedral.com.py/

## Tech Stack

- **Scraping**: Crawlee Python 1.0.x (PlaywrightCrawler for browser automation, httpx for API calls)
- **Language**: Python 3.11+
- **Database**: Supabase (PostgreSQL) - Real-time product storage with price history tracking
- **Data Warehouse**: Google BigQuery (future sync from Supabase)
- **Transformations**: dbt
- **Visualization**: Looker Studio
- **Deployment**: ~~Apify Platform~~ **DigitalOcean Droplet** (Apify too expensive for daily scraping)

## Cost Analysis & Deployment Decision

**Apify Platform Costs (TESTED - TOO EXPENSIVE):**
- Punto Farma Phase 2: ~$20 for 3h 40m runtime
- Estimated monthly cost for daily runs: **$1,200-1,800/month**
- **Decision**: Migrated to self-hosted DigitalOcean droplet

**DigitalOcean Droplet (RECOMMENDED):**
- **8GB RAM droplet**: $48/month (handles 20 concurrent browsers)
- **16GB RAM droplet**: $96/month (if 8GB insufficient)
- **Savings**: ~$1,100-1,700/month vs Apify
- Run scrapers 24/7 with no per-minute costs

## Data Extraction Requirements

**Core Product Information:**
- **Site Code** (pharmacy's internal SKU/product identifier)
- **Barcode** (EAN/UPC - universal product code, critical for cross-shop matching)
- Product name
- Brand (manufacturer/brand name)
- Product description (full product description/details)
- Category path

**Pricing Information:**
- Current price (regular/list price)
- Original price (if discounted)
- Discount percentage/amount
- Bank discount price (special price with bank card)
- Bank discount bank name
- Bank payment offers description

**Regulatory & Logistics:**
- **Requires Prescription** (boolean)
- Prescription type (e.g., "VENTA LIBRE", "CORTICOIDE")
- Payment methods
- Shipping options

**Metadata:**
- Pharmacy source
- Scrape timestamp (scraped_at)
- Product URL

## Project Structure

```
scrapers/           # Crawler implementations for each pharmacy
  ├── farma_oliva.py       # Traditional pagination scraper
  ├── punto_farma.py       # 2-phase: POST API → Playwright
  ├── farmacia_center.py   # 2-phase: Paginated HTML API → Playwright
  └── farmacia_catedral.py # 2-phase: JSON API → Playwright
storage/            # Supabase loader and database interactions
  └── supabase_loader.py   # Product upserts, URL tracking, price history
utils/              # Config and logging utilities
tests/              # Test suite
docs/               # Crawlee documentation (reference material)
main.py             # Apify Actor entry point (legacy, no longer used)
```

## Key Architecture Decisions

**2-Phase Scraping Strategy:**
All multi-page pharmacies use a 2-phase approach for reliability and performance:

1. **Phase 1: URL Collection** (Fast - API/pagination)
   - Use pagination APIs or HTML endpoints to collect all product URLs
   - Save URLs to `product_urls` table
   - **Speed**: 25 seconds to 2 minutes for 4,000-7,800 products

2. **Phase 2: Product Detail Scraping** (Slower - Playwright)
   - Query URLs from database where `product_name IS NULL` or `scraped_at < today`
   - Scrape product pages with Playwright for full details
   - Update products table with complete data
   - **Speed**: ~1 hour with 20 concurrent browsers for 6,800 products

**Why 2-Phase?**
- Separates fast URL discovery from slow page scraping
- Can re-run Phase 2 for stale/failed products without re-discovering URLs
- Phase 1 completes in minutes instead of hours
- Phase 2 can run with high concurrency (20 browsers)

**API Optimizations (90x Faster):**
- **Punto Farma**: POST API pagination (2 min vs 3 hours for URL collection)
- **Farmacia Catedral**: JSON API pagination (~25 sec for 4,900 products)
- **Farmacia Center**: Paginated HTML (~35 sec for 4,199 products)

**Database Schema:**
- **`products` table**: All product data (upserted on `pharmacy_source, site_code`)
- **`product_urls` table**: URL tracking for 2-phase scrapers (unique on `pharmacy_source, product_url`)
- **`price_history` table**: Automatic price change tracking via Postgres trigger
- **`scraping_runs` table**: Job metadata and stats

**Price History Tracking:**
- Postgres trigger automatically inserts to `price_history` when `current_price` changes
- Tracks: `product_id`, `old_price`, `new_price`, `changed_at`
- No application code needed - database-level automation

**Product Matching Strategy:**
1. **Barcode matching** (primary) - Products with same barcode = identical product
2. **AI similarity** (fallback) - For products without barcodes, use LLM embeddings
3. **Client catalog matching** - Compare scraped products to client's own pharmaceutical products

## Crawlee Configuration

**Concurrency Settings:**
```python
from crawlee import ConcurrencySettings

concurrency_settings = ConcurrencySettings(
    max_concurrency=20,  # 20 concurrent browsers for Phase 2
)

crawler = PlaywrightCrawler(
    concurrency_settings=concurrency_settings,
    request_handler_timeout=timedelta(seconds=30),  # 30s per product page
    max_request_retries=2,
    headless=True,
)
```

**Performance:**
- Phase 2 with 20 concurrent browsers: ~125 products/minute
- 6,800 products: ~55 minutes
- 4,200 products: ~35 minutes

## Implementation Status

### 1. Farma Oliva Scraper (COMPLETED)
**File**: `scrapers/farma_oliva.py`

**Strategy**: Single-phase traditional pagination (no URL collection needed)

**Features:**
- ✅ PlaywrightCrawler for JavaScript-rendered pages
- ✅ Category listing pagination (medicamentos + suplementos)
- ✅ Product detail extraction with BeautifulSoup
- ✅ Discount detection (original_price, discount_percentage, discount_amount)
- ✅ Real-time Supabase saving (products saved as they're scraped)
- ✅ Prescription requirement detection
- ✅ Product details extraction (Droga, Presentación, etc.)
- ✅ Image URL capture
- ✅ Breadcrumb category extraction
- ✅ Brand extraction fix (extract from breadcrumb "Marca BRAND")

**Key Selectors:**
- Product links: `.product a.ecommercepro-LoopProduct-link`
- Product name: `.single-product-header h1.product_title`
- Site code: `#producto-codigo`
- Barcode (EAN): `#producto-ean`
- Brand: Extract from breadcrumb `a.breadcrumb-item` containing "Marca"
- Current price: `#producto-precio`
- Original price (discounted): `#producto-precio-anterior`
- Discount badge: `.discount text` (SVG)
- Prescription: `.badge-pill`
- Next page: `a.next.page-numbers`

**Test Command:**
```bash
python -m scrapers.farma_oliva
```

**Expected Products**: ~4,471 (Medicamentos: 3,896 + Suplementos: 575)

---

### 2. Punto Farma Scraper (COMPLETED - OPTIMIZED)
**File**: `scrapers/punto_farma.py`

**Strategy**: 2-PHASE - POST API pagination → Playwright product scraping

**Phase 1: URL Collection via POST API (2 minutes) ⚡**
- ✅ Uses Next.js Server Action POST endpoint for pagination
- ✅ URL: `POST https://www.puntofarma.com.py/categoria/1/medicamentos`
- ✅ Payload: `["/productos/categoria/1?p={page}&orderBy=destacado&descuento="]`
- ✅ Response: `text/x-component` format with embedded JSON
- ✅ Parse JSON from response: `1:{"ok":true,"results":[...],"total":5277}`
- ✅ Extract product URLs from API response
- ✅ Save URLs to `product_urls` table
- ✅ **Speed**: 2 minutes for 5,277 products (90x faster than clicking)

**Phase 2: Product Scraping with Playwright (~55 minutes)**
- ✅ Query URLs from `product_urls` table
- ✅ Scrape product pages with Playwright (20 concurrent browsers)
- ✅ Extract full product details not available in API
- ✅ Update `products` table with complete data

**Why API is Better:**
- API returns partial data: codigo, codigoBarra, descripcion, precio, descuento, control
- But missing: full descripcionLarga, brand name, category path
- Still need Phase 2 for complete data

**Features:**
- ✅ POST API with Next.js Server Action headers
- ✅ JSON parsing from text/x-component response
- ✅ Product detail extraction from HTML
- ✅ Brand extraction from `<a class="category" href="/marca/...">`
- ✅ Product description from `<div class="atributos_body__wyXR6 accordion-body">`
- ✅ Bank discount extraction (Itaú QR Débito special pricing)
- ✅ Discount detection
- ✅ Real-time Supabase saving
- ✅ Concurrency: 20 browsers in Phase 2

**Test Commands:**
```bash
# Phase 1: Collect URLs (2 minutes)
python -m scrapers.punto_farma phase1

# Phase 2: Scrape products (~55 minutes for 6,800 products)
python -m scrapers.punto_farma phase2
```

**Expected Products**: ~5,277 (Medicamentos category)

**API Response Format:**
```
0:["$@1",["g1e-1giqLuQXaoHVgcmF4",null]]
2:T636,Product description text...
1:{"ok":true,"results":[{product_data}],"total":5277}
```

---

### 3. Farmacia Center Scraper (COMPLETED - OPTIMIZED)
**File**: `scrapers/farmacia_center.py`

**Strategy**: 2-PHASE - Paginated HTML API → Playwright product scraping

**Phase 1: URL Collection via Paginated HTML (~35 seconds) ⚡**
- ✅ Uses paginated HTML endpoint with `js=1` parameter
- ✅ URL: `GET https://www.farmacenter.com.py/medicamentos?js=1&pag={page}`
- ✅ 350 pages total, 12 products per page = 4,199 products
- ✅ Extract product links from HTML: `a.img[href*='/catalogo/']`
- ✅ Parse site_code from URL pattern: `_(\d+)_\d+$`
- ✅ Save URLs to `product_urls` table
- ✅ **Speed**: ~35 seconds for 4,199 products

**Phase 2: Product Scraping with Playwright (~35 minutes)**
- ✅ Query URLs from `product_urls` table
- ✅ Scrape product pages with Playwright (20 concurrent browsers)
- ✅ Extract complete product details
- ✅ Update `products` table

**Features:**
- ✅ httpx + BeautifulSoup for Phase 1 (fast HTML parsing)
- ✅ Site code + barcode split from combined field `10030348-7703281002468`
- ✅ Brand extraction from `data-tit` attribute (e.g., "Medicamentos ABBOTT")
- ✅ Discount detection (`precio lista` vs `precio venta`)
- ✅ Real-time Supabase saving
- ✅ Concurrency: 20 browsers in Phase 2

**Test Commands:**
```bash
# Phase 1: Collect URLs (~35 seconds)
python -m scrapers.farmacia_center phase1

# Phase 2: Scrape products (~35 minutes)
python -m scrapers.farmacia_center phase2
```

**Expected Products**: 4,199

---

### 4. Farmacia Catedral Scraper (COMPLETED - OPTIMIZED)
**File**: `scrapers/farmacia_catedral.py`

**Strategy**: 2-PHASE - JSON API pagination → Playwright product scraping

**Phase 1: URL Collection via JSON API (~25 seconds) ⚡**
- ✅ Uses JSON API endpoint with pagination
- ✅ URL: `GET https://www.farmaciacatedral.com.py/get-productos?page={page}&categoria=1`
- ✅ 246 pages total, ~20 products per page = 4,901 products
- ✅ Response: JSON with `paginacion.data[]` containing products
- ✅ Extract product URLs directly from JSON: `product.url_ver`
- ✅ Extract site_code from JSON: `product.codigo_articulo`
- ✅ Save URLs to `product_urls` table
- ✅ **Speed**: ~25 seconds for 4,901 products

**Phase 2: Product Scraping with Playwright (~40 minutes)**
- ✅ Query URLs from `product_urls` table
- ✅ Scrape product pages with Playwright (20 concurrent browsers)
- ✅ Extract JSON-LD structured data (primary source)
- ✅ HTML fallback for fields not in JSON-LD
- ✅ Update `products` table

**Features:**
- ✅ httpx for Phase 1 (JSON API calls)
- ✅ JSON-LD structured data extraction (primary source)
- ✅ HTML fallback extraction for all fields
- ✅ Brand extraction from JSON-LD or HTML
- ✅ Full product description from tabs
- ✅ Bank discount details (bank name, percentage, special price)
- ✅ Prescription requirement detection
- ✅ Discount detection
- ✅ Real-time Supabase saving
- ✅ Concurrency: 20 browsers in Phase 2

**Test Commands:**
```bash
# Phase 1: Collect URLs (~25 seconds)
python -m scrapers.farmacia_catedral phase1

# Phase 2: Scrape products (~40 minutes)
python -m scrapers.farmacia_catedral phase2
```

**Expected Products**: 4,901

**JSON API Response:**
```json
{
  "ok": true,
  "paginacion": {
    "data": [
      {
        "codigo_articulo": "12345",
        "url_ver": "https://www.farmaciacatedral.com.py/producto/...",
        ...
      }
    ],
    "total": 4901,
    "last_page": 246
  }
}
```

---

## Storage Module (COMPLETED)
**File**: `storage/supabase_loader.py`

**Features:**
- ✅ Real-time product upsert to Supabase
- ✅ URL tracking for 2-phase scrapers (`insert_product_urls()`)
- ✅ Get URLs to scrape (`get_urls_to_scrape()` - returns URLs with no product data or stale data)
- ✅ Scraping run tracking (start/complete with stats)
- ✅ Error handling and logging
- ✅ Upsert on conflict: `pharmacy_source, site_code`

**Database Tables:**
- `products`: All scraped product data (upserted)
- `product_urls`: URL tracking for 2-phase scrapers (unique constraint)
- `price_history`: Automatic price change tracking (Postgres trigger)
- `scraping_runs`: Job metadata and stats

**Price History Trigger:**
```sql
CREATE OR REPLACE FUNCTION track_price_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.current_price IS DISTINCT FROM NEW.current_price THEN
        INSERT INTO price_history (product_id, old_price, new_price, changed_at)
        VALUES (NEW.id, OLD.current_price, NEW.current_price, NOW());
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## Deployment

### DigitalOcean Droplet Setup (RECOMMENDED)

**Droplet Specifications:**
- **8GB RAM / 4 vCPUs**: $48/month (recommended starting point)
- **16GB RAM / 8 vCPUs**: $96/month (if 8GB insufficient)
- **Ubuntu 22.04 or 24.04 LTS**

**Installation Steps:**
1. Install Python 3.11+
2. Install Playwright: `playwright install chromium`
3. Install dependencies: `pip install -r requirements.txt`
4. Set up environment variables (`.env` file)
5. Configure cron for daily scraping runs

**Daily Scraping Cron:**
```bash
# Run all scrapers daily at 2 AM
0 2 * * * cd /path/to/pharma-intelligence && python run_all_scrapers.py >> /var/log/pharma-scraper.log 2>&1
```

**Estimated Runtime (with 20 concurrent browsers):**
- Farma Oliva: ~30 minutes (single-phase)
- Punto Farma: 2 min (Phase 1) + 55 min (Phase 2) = 57 minutes
- Farmacia Center: 35 sec (Phase 1) + 35 min (Phase 2) = 36 minutes
- Farmacia Catedral: 25 sec (Phase 1) + 40 min (Phase 2) = 41 minutes
- **Total**: ~2.5-3 hours per day

**Cost Comparison:**
- Apify: $1,200-1,800/month
- DigitalOcean 8GB: $48/month
- **Savings: ~$1,150-1,750/month** (96-98% cost reduction)

---

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run individual scrapers
python -m scrapers.farma_oliva
python -m scrapers.punto_farma phase1      # URL collection
python -m scrapers.punto_farma phase2      # Product scraping
python -m scrapers.farmacia_center phase1
python -m scrapers.farmacia_center phase2
python -m scrapers.farmacia_catedral phase1
python -m scrapers.farmacia_catedral phase2
```

## Testing & Validation

**Check scraping progress:**
```python
from storage.supabase_loader import SupabaseLoader
loader = SupabaseLoader()

# Check URLs collected
urls = await loader.get_urls_to_scrape('punto_farma')
print(f'URLs to scrape: {len(urls)}')

# Check products scraped
result = loader.client.table('products').select('id').eq('pharmacy_source', 'punto_farma').execute()
print(f'Products scraped: {len(result.data)}')
```

**Validate data quality:**
```sql
-- Count products by pharmacy
SELECT pharmacy_source, COUNT(*) FROM products GROUP BY pharmacy_source;

-- Check for missing barcodes
SELECT pharmacy_source, COUNT(*) FROM products WHERE barcode IS NULL GROUP BY pharmacy_source;

-- Check price history
SELECT * FROM price_history ORDER BY changed_at DESC LIMIT 10;
```

## Troubleshooting

### 404 Errors During Phase 2
**Issue**: Some product URLs return 404 (product removed from website)
**Solution**: This is normal - scraper retries 2 times and logs failures. Products may be discontinued.

### Memory Issues on Droplet
**Issue**: Out of memory with 20 concurrent browsers
**Solution**:
1. Reduce concurrency: `ConcurrencySettings(max_concurrency=10)`
2. Or upgrade to 16GB RAM droplet

### Playwright Browser Timeout
**Issue**: Browser crashes or timeouts
**Solution**: Increase timeout: `request_handler_timeout=timedelta(seconds=60)`

---

## Important Notes

- **Respect rate limits** - 0.1-0.5 second delays between API requests
- **Barcode is critical** - Without it, matching becomes much harder
- **Monitor website changes** - Pharmacy sites may change structure, breaking scrapers
- **Run Phase 1 daily** - Always collect fresh URLs before Phase 2
- **Price history is automatic** - Database trigger handles it, no code needed

## Reference Documentation

The `docs/` directory contains Crawlee Python documentation (examples, guides). Use it as reference when implementing scrapers, but do not modify it (read-only).
