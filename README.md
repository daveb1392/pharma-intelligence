# Pharma Intelligence - Multi-Pharmacy Price Comparison

A web scraping and data intelligence platform for pharmaceutical price comparison across Paraguayan pharmacy chains.

## Project Overview

This project scrapes drug and vitamin product data from 4 major Paraguayan pharmacy websites, performs intelligent product matching, and provides comparative analytics for a pharmaceutical laboratory client.

### Business Objectives

1. **Cross-Shop Price Comparison**: Match identical products across all 4 pharmacies using barcode identifiers and compare pricing, discounts, and promotions
2. **Competitive Intelligence**: Compare similar/competitor products to client's pharmaceutical product catalog
3. **Market Analytics**: Track pricing trends, promotional patterns, and market positioning

## Target Pharmacy Websites

1. **Farma Oliva** - https://www.farmaoliva.com.py/
2. **Punto Farma** - https://www.puntofarma.com.py/
3. **Farma Center** - https://www.farmacenter.com.py/
4. **Farmacia Catedral** - https://www.farmaciacatedral.com.py/

## Architecture

```
Railway (consumer app)          Hetzner (scraper server)
├── Next.js frontend            ├── Python scrapers (Crawlee + Playwright)
└── FastAPI backend             └── systemd timers (daily schedule)
         │                               │
         └──────── Supabase (PostgreSQL) ─┘
                   ├── products
                   ├── product_urls
                   ├── price_history (auto-trigger)
                   └── barcode_tracking_urls
```

- **Railway** hosts the consumer-facing app (frontend + backend API).
- **Hetzner** runs the scrapers on a daily schedule. No web serving.
- **Supabase** is the shared PostgreSQL database.

### Scraping Strategy

All multi-page pharmacies use a **2-phase approach**:

1. **Phase 1: URL Collection** (fast — API/pagination, seconds to minutes)
2. **Phase 2: Product Detail Scraping** (slower — Playwright with 20 concurrent browsers)

This separates fast URL discovery from slow page scraping. Phase 2 can re-run for stale/failed products without re-discovering URLs.

## Data Extraction

For each product: site code, barcode (EAN/UPC), name, brand, description, category, current price, original price, discount, bank discount details, prescription requirements, image URL, pharmacy source, and scrape timestamp.

## Installation

### Prerequisites

- Python 3.11+
- Supabase account (https://supabase.com)

### Setup

```bash
git clone <repo-url>
cd pharma-intelligence

pip install -r requirements.txt
playwright install --with-deps chromium

cp .env.example .env
# Edit .env with your Supabase credentials
```

## Usage

### Run All Scrapers

```bash
# Full scrape — all 4 pharmacies (Phase 1 + Phase 2)
./scripts/run_full_scrape.sh

# Single pharmacy
./scripts/run_full_scrape.sh punto_farma
```

### Run Individual Scrapers

```bash
# Farma Oliva (single-phase)
python -m scrapers.farma_oliva

# Punto Farma (2-phase)
python -m scrapers.punto_farma phase1
python -m scrapers.punto_farma phase2

# Farma Center (2-phase)
python -m scrapers.farmacia_center phase1
python -m scrapers.farmacia_center phase2

# Farmacia Catedral (2-phase)
python -m scrapers.farmacia_catedral phase1
python -m scrapers.farmacia_catedral phase2
```

### Daily Barcode Tracker

For targeted product tracking campaigns (specific barcodes only):

```bash
# One-time setup: populate tracking URLs from products table
python scripts/populate_tracking_urls.py

# Run tracker
python -m scrapers.daily_tracker

# Filter to single pharmacy
PHARMACY_FILTER=farma_oliva python -m scrapers.daily_tracker
```

See `docs/DAILY_TRACKER.md` for full documentation.

## Project Structure

```
scrapers/                   # Crawler implementations
  ├── farma_oliva.py        # Single-phase Playwright scraper
  ├── punto_farma.py        # 2-phase: POST API + Playwright
  ├── farmacia_center.py    # 2-phase: HTML API + Playwright
  ├── farmacia_catedral.py  # 2-phase: JSON API + Playwright
  └── daily_tracker.py      # Targeted barcode tracking
scripts/                    # Utility scripts
  ├── run_full_scrape.sh    # Run all scrapers (production entrypoint)
  ├── populate_tracking_urls.py
  └── test_tracker.py
storage/                    # Database interactions
  └── supabase_loader.py    # Product upserts, URL tracking, price history
utils/                      # Config and logging
backend/                    # FastAPI backend (deployed on Railway)
frontend/                   # Next.js frontend (deployed on Railway)
sql/                        # Database migrations
docs/                       # Documentation
```

## Pharmacy Naming Convention

The canonical `pharmacy_source` values stored in the database are:

| Pharmacy | `pharmacy_source` value |
|----------|------------------------|
| Farma Oliva | `farma_oliva` |
| Punto Farma | `punto_farma` |
| Farma Center | `farma_center` |
| Farmacia Catedral | `farmacia_catedral` |

## Estimated Runtime

With 20 concurrent Playwright browsers on 8GB RAM:

| Pharmacy | Phase 1 | Phase 2 | Total |
|----------|---------|---------|-------|
| Farma Oliva | — | ~30 min | ~30 min |
| Punto Farma | ~2 min | ~55 min | ~57 min |
| Farma Center | ~35 sec | ~35 min | ~36 min |
| Farmacia Catedral | ~25 sec | ~40 min | ~41 min |
| **Total** | | | **~2.5 hours** |

## Resources

- [Crawlee Python Documentation](https://crawlee.dev/python/)
- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Python Client](https://supabase.com/docs/reference/python/introduction)
