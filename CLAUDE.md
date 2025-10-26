# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Pharma Intelligence** - Multi-pharmacy price comparison platform for a pharmaceutical laboratory client. Scrapes 4 Paraguayan pharmacy websites, performs intelligent product matching using barcodes and AI, and provides competitive analytics via BigQuery + dbt + Looker Studio.

## Target Pharmacy Websites

1. Farma Oliva - https://www.farmaoliva.com.py/
2. Punto Farma - https://www.puntofarma.com.py/
3. Farma Center - https://www.farmacenter.com.py/
4. Farmacia Catedral - https://www.farmaciacatedral.com.py/

## Tech Stack

- **Scraping**: Crawlee Python (PlaywrightCrawler for JS-heavy sites)
- **Language**: Python 3.11+
- **Database**: Supabase (PostgreSQL) - Real-time product storage
- **Data Warehouse**: Google BigQuery (future sync from Supabase)
- **Transformations**: dbt
- **Visualization**: Looker Studio
- **Deployment**: Apify Platform OR GitHub Actions (TBD)

## Data Extraction Requirements

**Core Product Information:**
- **Site Code** (pharmacy's internal SKU/product identifier)
- **Barcode** (EAN/UPC - universal product code, critical for cross-shop matching)
- Product name
- Brand (manufacturer/brand name)
- Product description (full product description/details)
- Category

**Pricing Information:**
- Current price (regular/list price)
- Original price (if discounted)
- Discount percentage/amount
- Bank discount price (special price with bank card - 2 sites have this)
- Bank payment offers

**Regulatory & Logistics:**
- **Requires Prescription** (boolean - 3 sites have this field)
- Payment methods
- Shipping options

**Metadata:**
- Pharmacy source
- Scrape timestamp
- Product URL

## Project Structure

```
scrapers/           # Crawler implementations for each pharmacy
matching/           # Barcode and AI-based product matching
storage/            # BigQuery loader and schemas
utils/              # Config and logging utilities
tests/              # Test suite
docs/               # Crawlee documentation (reference material)
```

## Key Architecture Decisions

**Why Crawlee?**
- Open-source, can run on Apify OR self-hosted (GitHub Actions)
- Asyncio-based for performance
- Built-in retry logic, error handling, persistent queues
- Supports both HTTP (fast) and headless browser (JS-heavy sites)

**Why BigQuery?**
- Native Looker Studio integration (required for visualization)
- Handles time-series pricing data efficiently
- dbt compatible for transformations
- Scalable for daily scrapes across thousands of products

**Product Matching Strategy:**
1. **Barcode matching** (primary) - Products with same barcode = identical product
2. **AI similarity** (fallback) - For products without barcodes, use LLM embeddings
3. **Client catalog matching** - Compare scraped products to client's own pharmaceutical products

## Development Workflow

1. **Start with one pharmacy** to establish scraping pattern
2. **Inspect website structure** (use browser DevTools to find product selectors)
3. **Choose crawler type**:
   - Use `BeautifulSoupCrawler` if HTML is static (faster)
   - Use `PlaywrightCrawler` if site requires JavaScript rendering
4. **Extract required fields** and validate barcode presence
5. **Test locally** with `max_requests_per_crawl` limit
6. **Load to BigQuery** staging tables
7. **Replicate for other 3 pharmacies**

## Crawlee Patterns (from docs/ reference)

**Basic crawler structure:**
```python
import asyncio
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(max_requests_per_crawl=50)

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        # Extract data
        product = {
            'name': await context.page.locator('.product-name').text_content(),
            'price': await context.page.locator('.price').text_content(),
        }
        await context.push_data(product)  # Save to dataset
        await context.enqueue_links()     # Discover more URLs

    await crawler.run(['https://example.com'])

if __name__ == '__main__':
    asyncio.run(main())
```

**Key Crawlee APIs:**
- `context.push_data(data)` - Save extracted data
- `context.enqueue_links()` - Queue discovered URLs
- `context.log.info()` - Logging
- `context.page` - Playwright page object (for PlaywrightCrawler)
- `context.soup` - BeautifulSoup object (for BeautifulSoupCrawler)

## Common Commands

```bash
# Install dependencies
pip install 'crawlee[all]'
playwright install

# Run scraper locally
python -m scrapers.farma_oliva

# Deploy to Apify (if using Apify)
apify push
apify call

# Run via GitHub Actions
gh workflow run scrape.yml
```

## Important Notes

- **Respect rate limits** - Add delays to avoid overwhelming pharmacy servers
- **Barcode is critical** - Without it, matching becomes much harder
- **Validate data** - Check for missing/malformed fields before BigQuery load
- **Monitor website changes** - Pharmacy sites may change structure, breaking scrapers
- **Log extensively** - Essential for debugging extraction issues

## Implementation Status

### 1. Farma Oliva Scraper (COMPLETED)
**File**: `scrapers/farma_oliva.py`

**Navigation Strategy**: Traditional pagination with "Next" button

**Features Implemented:**
- ✅ PlaywrightCrawler for JavaScript-rendered pages
- ✅ Category listing pagination (medicamentos + suplementos)
- ✅ Product detail extraction with BeautifulSoup
- ✅ Discount detection (original_price, discount_percentage, discount_amount)
- ✅ Real-time Supabase saving (products saved as they're scraped)
- ✅ Prescription requirement detection
- ✅ Product details extraction (Droga, Presentación, etc.)
- ✅ Image URL capture
- ✅ Breadcrumb category extraction

**Key Selectors:**
- Product links: `.product a.ecommercepro-LoopProduct-link`
- Product name: `.single-product-header h1.product_title`
- Site code: `#producto-codigo`
- Barcode (EAN): `#producto-ean`
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

**Known Issues:**
1. **Pagination stops early for medicamentos** - Only getting ~21 pages instead of 162+ pages
   - Suplementos pagination works correctly
   - May be hitting Crawlee internal limit or pagination selector failing after certain page
   - Next button selector `a.next.page-numbers` works but stops discovering pages
2. **macOS keychain popup** - Playwright triggers permission request on macOS
   - User must click "Deny" or "Always Allow" to dismiss
   - Cannot be fully disabled programmatically

---

### 2. Punto Farma Scraper (COMPLETED)
**File**: `scrapers/punto_farma.py`

**Navigation Strategy**: 2-PHASE APPROACH (URL collection → Product scraping)

**Why 2-Phase Approach:**
- Punto Farma has ~520 pages requiring "Cargar más" button clicks
- Clicking through all pages takes ~260 seconds (exceeds typical handler timeouts)
- Separating URL collection from product scraping improves reliability and allows parallel execution

**Phase 1: URL Collection**
- ✅ Click "Cargar más" button up to 520 times to load all products
- ✅ Extract product URLs from each page load
- ✅ Save URLs progressively to `product_urls` table in Supabase
- ✅ In-memory deduplication with `set()` + database unique constraint
- ✅ 4-hour timeout to handle long clicking sessions without interruption
- ✅ Runs on Apify with input: `{"pharmacy": "punto_farma", "punto_farma_phase": "phase1"}`

**Phase 2: Product Scraping**
- ✅ Query all URLs from `product_urls` table (no pagination limit)
- ✅ Scrape each product page and save to `products` table
- ✅ 30-second timeout per product page
- ✅ Runs on Apify with input: `{"pharmacy": "punto_farma", "punto_farma_phase": "phase2"}`
- ⚠️ Re-scrapes ALL URLs every run (no tracking of already-scraped URLs)
- ✅ Upsert updates existing products (safe to re-scrape)

**Features Implemented:**
- ✅ PlaywrightCrawler with 4-hour timeout for Phase 1
- ✅ "Cargar más" button clicking with retry logic
- ✅ Product detail extraction from HTML
- ✅ Brand extraction from `<a class="category" href="/marca/...">`
- ✅ Product description from `<div class="atributos_body__wyXR6 accordion-body">`
- ✅ Bank discount extraction (Itaú QR Débito special pricing)
- ✅ Discount detection (original_price, discount_percentage, discount_amount)
- ✅ Real-time Supabase saving
- ✅ Breadcrumb category extraction
- ✅ Image URL capture

**Key Selectors:**
- Product links: `a[href*='/producto/']`
- Product name: `h1`
- Site code: `.codigo span.fw-bold.user-select-all` (first)
- Barcode: `.codigo span.user-select-all` (last)
- Brand: `a.category[href*='/marca/']`
- Description: `.atributos_body__wyXR6.accordion-body`
- Current price: `.precio-con-descuento span.precio-lg`
- Original price: `.precio-regular del.precio-sin-descuento`
- Discount: `.precio-regular div[style*='background-color']`
- Bank discount: `h6:has-text('Con Itau')` + price in same container
- "Cargar más" button: `button.btn.btn-primary:has-text('Cargar más')`

**Test Commands:**
```bash
# Local testing - Phase 1 (collect URLs)
python -m scrapers.punto_farma phase1

# Local testing - Phase 2 (scrape products)
python -m scrapers.punto_farma phase2

# Apify deployment - Use dropdown to select phase
```

**Expected Products**: ~6,240 (Medicamentos: 440 pages × 12 = 5,280 + Nutrición: 80 pages × 12 = 960)

**Running on Apify:**
1. **Phase 1**: Select `{"pharmacy": "punto_farma", "punto_farma_phase": "phase1"}` → Collects all URLs
2. **Phase 2**: Select `{"pharmacy": "punto_farma", "punto_farma_phase": "phase2"}` → Scrapes all collected URLs
3. **Parallel execution**: Can run Phase 1 continuously while running Phase 2 on already-collected URLs
4. **Re-running Phase 2**: Safe to run multiple times (upserts existing products with fresh data)

**Database Tables:**
- `product_urls`: Stores all collected URLs (unique constraint on `pharmacy_source, product_url`)
- `products`: Stores scraped product data (upserted based on `pharmacy_source, site_code`)

---

### 3. Farmacia Center Scraper (COMPLETED)
**File**: `scrapers/farmacia_center.py`

**Navigation Strategy**: Sequential navigation using "Siguiente" (Next) button on product pages

**Features Implemented:**
- ✅ PlaywrightCrawler with sequential product navigation
- ✅ "Siguiente" button auto-navigation through all products
- ✅ Site code + barcode split from combined field `10030348-7703281002468`
- ✅ Brand extraction from `data-tit` attribute (e.g., "Medicamentos ABBOTT")
- ✅ Discount detection (`precio lista` vs `precio venta`)
- ✅ Optional product description
- ✅ Real-time Supabase saving
- ✅ Auto-enqueues next product URL after each scrape

**Key Selectors:**
- Product name: `h1.tit`
- Site code + Barcode: `.cod` (split on `-`)
- Brand: `#central[data-tit]` (extract from "Medicamentos BRAND")
- Description: `.desc p`
- Original price: `.precios del.precio.lista .monto`
- Current price: `.precios strong.precio.venta .monto`
- Image: `img[alt]` (use `data-src-g` or `src`)
- Next button: `button.btnSiguiente.btnNav`
- Product counter: `.nav .info .actual` and `.tot`

**Test Command:**
```bash
python -m scrapers.farmacia_center
```

**Expected Products**: 3,443

**How it works:**
- Starts from medicamentos category page
- Navigates to first product
- Scrapes product data
- Clicks "Siguiente" button to go to next product
- Repeats until last product (when URL doesn't change)
- Avoids lazy scroll issues by using sequential navigation

---

### 4. Farmacia Catedral Scraper (COMPLETED)
**File**: `scrapers/farmacia_catedral.py`

**Navigation Strategy**: Lazy scroll on category pages, then scrape all discovered products

**Features Implemented:**
- ✅ PlaywrightCrawler with lazy scroll on category listings
- ✅ JSON-LD structured data extraction (primary source)
- ✅ HTML fallback extraction for all fields
- ✅ Brand extraction from JSON-LD or HTML
- ✅ Full product description from tabs (prioritizes detailed description)
- ✅ Bank discount details (bank name, percentage, special price)
- ✅ Prescription requirement detection
- ✅ Stock availability tracking
- ✅ Discount detection (percentage tag + price difference)
- ✅ Real-time Supabase saving
- ✅ Category path from breadcrumbs

**Key Selectors (JSON-LD + HTML):**
- JSON-LD: `script[type="application/ld+json"]`
- Product name: JSON-LD `name` or `h1.title-ficha`
- Site code (SKU): JSON-LD `sku` or `.codigo-ficha`
- Barcode: `.barra-ficha` (regex: `CÓD. BARRAS: (.+)`)
- Brand: JSON-LD `brand.name` or `a.title-marca`
- Description: `#home-tab-pane` (full) or `#profile-tab-pane` (short) or JSON-LD `description`
- Current price: JSON-LD `offers.price` or `.precio-web` (first price)
- Original price: `.precio-web span` (second price)
- Discount tag: `.tag-descuentos` (e.g., `-50%`)
- Bank discount: `.list-itau li` (percentage and price)
- Bank name: `.title-itau img[alt]` (extract from alt text)
- Prescription: `.alert.alert-warning` (check for "receta")
- Stock: `.stock-ficha` (check for "disponible")
- Image: JSON-LD `image[0]` or `img[alt='Imagen de Producto']`
- Category: `ol.breadcrumb a.breadcrumb-item`

**Test Command:**
```bash
python -m scrapers.farmacia_catedral
```

**Expected Products**: Unknown (Medicamentos + Suplementos categories)

**How it works:**
- Scrolls category pages until no new content loads (max 100 scroll attempts)
- Extracts all product links after full page load
- Deduplicates URLs before enqueueing
- Scrapes product pages using JSON-LD as primary source
- Falls back to HTML selectors if JSON-LD is missing/malformed
- Extracts bank discount, prescription, and stock data (not in JSON-LD)

### Storage Module (COMPLETED)
**File**: `storage/supabase_loader.py`

**Features:**
- ✅ Real-time product upsert to Supabase
- ✅ Scraping run tracking (start/complete with stats)
- ✅ Error handling and logging
- ✅ Upsert on conflict: `pharmacy_source,site_code`

**Supabase Tables:**
- `products` - All scraped product data
- `scraping_runs` - Scraping job metadata and stats

### Configuration (COMPLETED)
**Files**: `utils/config.py`, `.env`

**Settings:**
- Supabase URL and API key
- Max requests per crawl: 100,000
- Request delay: 500ms
- Max concurrency: 5
- Log level: INFO

### Utils (COMPLETED)
**Files**: `utils/logger.py`, `utils/config.py`

**Features:**
- ✅ Loguru-based logging with colors
- ✅ Pydantic settings management
- ✅ Environment variable loading
- ✅ Pharmacy URL configuration

## Troubleshooting

### Pagination Not Working
**Problem**: Scraper only gets first page or stops after a few pages.
**Solution**:
1. Check selector: Use `a.next.page-numbers` not `.pagination .next:not(.disabled)`
2. Verify JavaScript execution: Add `await context.page.wait_for_timeout(1000)`
3. Clear Crawlee cache: `rm -rf storage/datasets storage/request_queues storage/key_value_stores`

### Products Not Saving to Supabase
**Problem**: Products scraped but not in database.
**Solution**:
1. Ensure `db_loader_instance` is set as global variable
2. Check Supabase credentials in `.env`
3. Verify table schema matches product data structure
4. Check logs for upsert errors

### Discount Data Missing
**Problem**: Products with discounts showing NULL for discount fields.
**Solution**:
1. Ensure JavaScript execution wait time (1000ms) before extracting HTML
2. Discounts may be time-sensitive (expire at midnight)
3. Check selectors: `#producto-precio-anterior` and `.discount text`

### macOS Keychain Password Popup
**Problem**: macOS asks for password when running Playwright.
**Solution**:
- Click "Deny" (scraper continues working) OR
- Click "Always Allow" (won't ask again)
- This is a Playwright/Chromium behavior and cannot be disabled

## Testing Scrapers

### Running Individual Scrapers

Each scraper can be run independently for testing:

```bash
# Farma Oliva (traditional pagination)
python -m scrapers.farma_oliva

# Punto Farma (infinite scroll with "Cargar más")
python -m scrapers.punto_farma

# Farmacia Center (sequential navigation with "Siguiente")
python -m scrapers.farmacia_center

# Farmacia Catedral (lazy scroll + JSON-LD)
python -m scrapers.farmacia_catedral
```

### Test Mode Configuration

To limit requests during testing, update `.env`:

```bash
# Full production run
MAX_REQUESTS_PER_CRAWL=100000

# Small test run (e.g., 50 products)
MAX_REQUESTS_PER_CRAWL=50
```

For Punto Farma, you can also modify the `max_pages` variable in the scraper:
```python
# In scrapers/punto_farma.py, line ~212
max_pages = 3  # TEST: Start with 3 pages, change to 440 for full run
```

### Clearing Crawlee Cache

If scrapers are behaving unexpectedly (duplicate requests, stale data), clear the cache:

```bash
rm -rf storage/datasets storage/request_queues storage/key_value_stores
```

### Monitoring Scraping Progress

1. **Console logs** - Real-time progress with Loguru colored output
2. **Supabase dashboard** - Check `products` table for inserted records
3. **Scraping runs table** - Check `scraping_runs` for job metadata and stats

### Expected Output

Successful scraper run will show:
```
2025-01-XX XX:XX:XX | INFO | Starting [pharmacy_name] scraper...
2025-01-XX XX:XX:XX | INFO | Processing category listing: [url]
2025-01-XX XX:XX:XX | INFO | Found X product links
2025-01-XX XX:XX:XX | INFO | Processing product page: [url]
2025-01-XX XX:XX:XX | INFO | Saved to Supabase: [product_name]
2025-01-XX XX:XX:XX | INFO | Scraping completed: X products scraped and saved to Supabase
```

### Validating Scraped Data

Check Supabase for data quality:

```sql
-- Count products by pharmacy
SELECT pharmacy_source, COUNT(*)
FROM products
GROUP BY pharmacy_source;

-- Check for missing barcodes (critical for matching)
SELECT pharmacy_source, COUNT(*)
FROM products
WHERE barcode IS NULL
GROUP BY pharmacy_source;

-- Check for products with discounts
SELECT pharmacy_source, COUNT(*)
FROM products
WHERE discount_percentage IS NOT NULL
GROUP BY pharmacy_source;

-- Check for bank discounts (Farma Oliva and Farmacia Catedral only)
SELECT pharmacy_source, COUNT(*)
FROM products
WHERE bank_discount_price IS NOT NULL
GROUP BY pharmacy_source;
```

## Reference Documentation

The `docs/` directory contains Crawlee Python documentation (examples, guides). Use it as reference when implementing scrapers, but do not modify it (read-only).
