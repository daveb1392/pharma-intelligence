# TODO - Pharma Intelligence

## Status Summary (March 2026)

- **Consumer platform (Railway)**: LIVE at https://preciofarma-web-production.up.railway.app
- **Scrapers**: All 4 working for medicamentos only. Need updates for all categories + Hetzner deployment.
- **Current DB**: ~17,953 products (medicamentos only)

---

## 1. SCRAPER UPDATES - Expand to All Categories

### 1.1 Farma Oliva - REWRITE to 2-Phase

**Priority: HIGH** | Currently: single-phase Playwright (slow, medicamentos only)

The site migrated from WooCommerce to **Dattamax** platform. Old pagination selectors are gone but catalog pages still work.

**What changed:**
- New platform (Dattamax, not WooCommerce anymore)
- URL pattern: `/catalogo/medicamentos-c3.{page}` (dot-separated pages)
- `?ajax=true` parameter returns lightweight HTML (just product grid)
- Product detail selectors still work (`#producto-codigo`, `#producto-ean`, etc.)
- Now has 11,403 products total (was ~4,471)

**Phase 1 (URL Collection via httpx + ?ajax=true):**
- Endpoint: `GET https://www.farmaoliva.com.py/catalogo.{page}?ajax=true`
- 476 pages total (24 products/page), ~16 min
- Or per-category: `/catalogo/medicamentos-c3.{page}?ajax=true` etc.
- Product links: `a.ecommercepro-LoopProduct-link[href]`
- Site code from image filename: `/{site_code}-{barcode}-{name}.jpg`

**Phase 2 (Playwright product detail):**
- Selectors still work: `#producto-codigo`, `#producto-ean`, `a.logo-marca`, etc.
- ~90 min for all 11,403 products at 20 concurrent browsers

**Categories (all have `?ajax=true` support):**
| Category | Slug | Products |
|----------|------|----------|
| Medicamentos | medicamentos-c3 | 3,947 |
| Belleza | belleza-c118 | 1,887 |
| Cuidado Personal | cuidado-personal-c1 | 1,652 |
| Dermocosmetica | dermocosmetica-c119 | 1,052 |
| Infantiles | infantiles-c10 | 1,041 |
| Suplementos | suplementos-nutricionales-c5 | 591 |
| Fragancias | fragancias-c24 | 487 |
| Perfumes | perfumes-c25 | 376 |
| Juguetes y Peluches | juguetes-y-peluches-c16 | 194 |
| Panales | panales-c42 | 97 |
| Bienestar Sexual | bienestar-sexual-c228 | 68 |
| **TOTAL** | `/catalogo` (no filter) | **11,403** |

**Simplest approach:** Use `/catalogo.{page}?ajax=true` without category filter to get all 11,403 at once.

---

### 1.2 Punto Farma - Add All Categories

**Priority: HIGH** | Currently: medicamentos (5,360) + nutricion-y-deporte only

The POST API works fine. Just need to add more category IDs to the scraper.

**Top-level categories to add (from 426 total discovered):**
| ID | Name | Description |
|----|------|-------------|
| 1 | medicamentos | Already scraped |
| 2 | perfumes-y-fragancias | Perfumes & Fragrances |
| 3 | bebe-y-mama | Baby & Mother |
| 4 | cosmeticos | Cosmetics |
| 5 | higiene | Hygiene |
| 6 | salud | Health |
| 238 | nutricion-y-deporte | Already scraped |

**Implementation:** Add top-level category IDs to the `categories` list in `collect_urls_from_api()`. Many of the 426 categories are subcategories — only need the top-level ones to avoid duplicates. Need to verify which are top-level vs subcategory to avoid double-counting.

**Note:** The `next-action` header hash (`48e9f2eca478537e00a58539a9f9edcf2e1dff77`) may change on site deploys. If Phase 1 breaks, check if this hash needs updating by inspecting a request in browser DevTools.

---

### 1.3 Farmacia Center - Add All Categories + Fix Images

**Priority: HIGH** | Currently: medicamentos only (4,232)

**Image fix:** Already done (uncommitted change in `scrapers/farmacia_center.py`). Finds catalog images instead of logos. Needs commit.

**Categories to add (8 total, 9,894 products):**
| Category | URL slug | Products | Pages |
|----------|----------|----------|-------|
| Medicamentos | `/medicamentos` | 4,232 | 353 |
| Belleza | `/belleza` | 2,440 | 203 |
| Higiene | `/higiene` | 1,503 | 125 |
| Cuidado de la Salud | `/cuidado-de-la-salud` | 630 | 53 |
| Bebes | `/bebes` | 463 | 39 |
| Bazar y Hogar | `/bazar-y-hogar` | 266 | 22 |
| Alimentos | `/alimentos` | 196 | 17 |
| Infantiles | `/infantiles` | 164 | 14 |
| **TOTAL** | | **9,894** | |

**Implementation:** Update `collect_urls_from_pages()` to loop through all category slugs instead of just `/medicamentos`. The `?js=1&pag={page}` pattern works for all categories.

---

### 1.4 Farmacia Catedral - Add All Categories

**Priority: HIGH** | Currently: categoria=1 (medicamentos, 4,857)

The JSON API works perfectly. Just need to scrape more category IDs.

**Top categories (244 total with products, 32,211 total products):**
| ID | Name | Products |
|----|------|----------|
| 1 | medicamentos | 4,857 |
| 46 | cuidado-corporal | 3,800 |
| 67 | cuidado-de-la-piel | 1,535 |
| 132 | maquillajes | 861 |
| 248 | cuidado-personal | 872 |
| 80 | cuidado-capilar | 830 |
| 35 | suplemento-vitaminico-y-mineral | 749 |
| 70 | cremas-faciales-y-corporales | 745 |
| 94 | bebes-y-maternidad | 725 |
| 84 | dermocosmetica | 578 |
| 125 | perfumes-y-fragancias | 435 |

**Warning:** Many subcategories overlap (products appear in parent + child category). Scraping all 244 IDs would yield duplicates. Either:
1. Use only top-level category IDs (need to identify parent/child relationships)
2. OR skip `categoria` param entirely — test if `categoria=0` or no param returns all products
3. OR use deduplication by `url_ver` in `product_urls` table (already has unique constraint)

**Implementation:** Update `collect_urls_from_api()` to iterate over a list of category IDs. Existing unique constraint on `product_urls(pharmacy_source, product_url)` handles dedup automatically.

---

## 2. HETZNER DEPLOYMENT

**Priority: HIGH** | Currently: scrapers run locally only

### 2.1 Provision Hetzner VPS
- **Recommended:** CX31 (8GB RAM / 4 vCPUs) ~$7.50/month
- **If needed:** CX41 (16GB RAM / 8 vCPUs) ~$14/month
- Ubuntu 24.04 LTS

### 2.2 Server Setup Script
Create a setup script that installs:
- Python 3.11+
- Playwright + Chromium: `playwright install --with-deps chromium`
- pip dependencies: `pip install -r requirements.txt`
- .env file with Supabase credentials
- Clone the repo

### 2.3 Cron Schedule
```bash
# Daily full scrape at 2 AM Paraguay time (UTC-4 = 6 AM UTC)
# Phase 1 for all pharmacies (fast, ~20 min total)
0 6 * * * cd /opt/pharma-intelligence && python -m scrapers.farma_oliva phase1 >> /var/log/pharma/farma_oliva.log 2>&1
5 6 * * * cd /opt/pharma-intelligence && python -m scrapers.punto_farma phase1 >> /var/log/pharma/punto_farma.log 2>&1
10 6 * * * cd /opt/pharma-intelligence && python -m scrapers.farmacia_center phase1 >> /var/log/pharma/farmacia_center.log 2>&1
15 6 * * * cd /opt/pharma-intelligence && python -m scrapers.farmacia_catedral phase1 >> /var/log/pharma/farmacia_catedral.log 2>&1

# Phase 2 for all pharmacies (staggered, each ~45-90 min)
30 6 * * * cd /opt/pharma-intelligence && python -m scrapers.farma_oliva phase2 >> /var/log/pharma/farma_oliva.log 2>&1
30 8 * * * cd /opt/pharma-intelligence && python -m scrapers.punto_farma phase2 >> /var/log/pharma/punto_farma.log 2>&1
30 10 * * * cd /opt/pharma-intelligence && python -m scrapers.farmacia_center phase2 >> /var/log/pharma/farmacia_center.log 2>&1
30 12 * * * cd /opt/pharma-intelligence && python -m scrapers.farmacia_catedral phase2 >> /var/log/pharma/farmacia_catedral.log 2>&1
```

### 2.4 Monitoring
- Log rotation for scraper logs
- Health check script (verify products updated today)
- Optional: Slack/email alerts on failure

---

## 3. PENDING FIXES

- [ ] **Commit farmacia_center.py image fix** - already in working tree, just needs commit
- [ ] **Update utils/config.py PHARMACY_URLS** with all categories for each pharmacy
- [ ] **Clean up docs/** - agent created `PUNTO_FARMA_CATEGORIES.csv` and `.md` during research, remove if not needed

---

## 4. ESTIMATED PRODUCT COUNTS (After Expansion)

| Pharmacy | Current (meds only) | After expansion |
|----------|-------------------|-----------------|
| Farma Oliva | ~4,471 | ~11,403 |
| Punto Farma | ~5,360 | ~8,000+ (TBD) |
| Farmacia Center | ~4,232 | ~9,894 |
| Farmacia Catedral | ~4,857 | ~15,000+ (TBD, dedup needed) |
| **TOTAL** | **~17,953** | **~44,000+** |

---

## 5. FUTURE / NICE-TO-HAVE

- [ ] BigQuery sync from Supabase
- [ ] dbt transformations
- [ ] Looker Studio dashboards
- [ ] AI product matching (for products without barcodes)
- [ ] Client catalog matching
- [ ] Custom domain for preciofarma
