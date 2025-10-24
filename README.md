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

## Data Extraction Requirements

For each product, extract:

### Core Product Information
- **Site Code** (pharmacy's internal SKU/product identifier)
- **Barcode** (EAN/UPC - universal product code, critical for cross-shop matching)
- **Product Name**
- **Brand** (manufacturer/brand name)
- **Product Description** (full product description/details)
- **Category** (drugs, vitamins, supplements, etc.)

### Pricing Information
- **Current Price** (regular/list price)
- **Original Price** (if discounted)
- **Discount Percentage/Amount**
- **Bank Discount Price** (special price with bank card - 2 sites have this)
- **Bank Discount Bank Name** (which bank offers the discount, e.g., "Banco Itaú", "Banco Continental")
- **Bank Payment Offers** (special bank promotions/installment plans)

### Regulatory & Logistics
- **Requires Prescription** (boolean - if product requires medical prescription; 3 sites have this)
- **Payment Methods** (accepted payment options)
- **Shipping Options** (delivery methods and costs)

### Metadata
- **Pharmacy Source** (which website)
- **Scrape Timestamp**
- **Product URL**

## Technical Architecture

### Scraping Stack

**Framework**: [Crawlee Python](https://crawlee.dev/python/) - Open-source web scraping and browser automation library
- Asyncio-based for high performance
- Built-in retry logic and error handling
- Supports both HTTP (BeautifulSoupCrawler) and headless browser (PlaywrightCrawler) modes
- Persistent request queues and storage

**Language**: Python 3.11+

**Crawler Types**:
- Use `BeautifulSoupCrawler` for static HTML sites (faster, lower resource usage)
- Use `PlaywrightCrawler` for JavaScript-heavy sites requiring browser rendering

### Deployment Options

**Option 1: Apify Platform** (Managed)
- Hosted execution environment
- Built-in scheduling and monitoring
- Integrated with Crawlee (same parent company)
- See [Apify SDK Documentation](https://docs.apify.com/sdk/python/)

**Option 2: GitHub Actions** (Self-Hosted)
- Run scrapers on scheduled workflows
- Free for public repos, usage limits for private
- More control over execution environment
- Requires manual setup of storage and error monitoring

**Decision Criteria**: Start with Apify for faster development, migrate to GitHub Actions if cost becomes a concern

### Data Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ SCRAPING LAYER (Crawlee)                                    │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│ │ Farma Oliva  │ │  Punto Farma │ │ Farma Center │  etc.   │
│ └──────────────┘ └──────────────┘ └──────────────┘         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ MATCHING LAYER (AI-Powered)                                 │
│ - Barcode-based matching (primary key)                      │
│ - AI similarity matching for products without barcodes      │
│ - Product normalization and deduplication                   │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ STORAGE LAYER (BigQuery)                                    │
│ - Raw scraped data (staging tables)                         │
│ - Matched products (fact tables)                            │
│ - Historical pricing (time-series)                          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ TRANSFORMATION LAYER (dbt)                                  │
│ - Data modeling and transformations                         │
│ - Business logic and aggregations                           │
│ - Data quality tests                                        │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ VISUALIZATION LAYER (Looker Studio)                         │
│ - Price comparison dashboards                               │
│ - Discount trend analysis                                   │
│ - Competitive positioning reports                           │
└─────────────────────────────────────────────────────────────┘
```

### Data Warehouse: Supabase (Primary) + BigQuery (Analytics)

**Primary Database: Supabase (PostgreSQL)**

**Why Supabase First**:
- ✅ **Auto-generated REST & GraphQL APIs** - No need to build custom API layer
- ✅ **Real-time subscriptions** - Monitor scrapes in real-time
- ✅ **PostgreSQL power** - Full-text search, triggers, functions for data standardization
- ✅ **Easier product name normalization** - Iterative data cleaning with UPDATE queries
- ✅ **Row-level security** - Built-in access control for client
- ✅ **Developer-friendly** - Local PostgreSQL development, generous free tier
- ✅ **Built-in Auth** - If building a dashboard/API for client

**Secondary Warehouse: BigQuery (Optional)**

**When to add BigQuery**:
- Client needs Looker Studio dashboards (no native Supabase connector)
- Data volume exceeds Supabase free tier (500MB)
- Need heavy time-series analytics and aggregations

**Hybrid Architecture**:
```
Scrapers → Supabase (operational DB, API, standardization)
              ↓
         [Daily Sync Script]
              ↓
         BigQuery (analytics warehouse)
              ↓
         Looker Studio (reporting)
```

**Sync Strategy**: Simple Python script runs daily/hourly to copy Supabase data to BigQuery for analytics

### Product Matching Strategy

**Phase 1: Barcode Matching** (High Confidence)
```python
# Products with identical barcodes = same product
SELECT
  barcode,
  pharmacy_source,
  product_name,
  price,
  discount
FROM scraped_products
WHERE barcode IS NOT NULL
GROUP BY barcode
HAVING COUNT(DISTINCT pharmacy_source) > 1  -- Found in multiple pharmacies
```

**Phase 2: AI-Powered Similarity Matching** (For products without barcodes)
- Use LLM embeddings (OpenAI, Claude, or local models) to vectorize product names and descriptions
- Calculate semantic similarity scores
- Human-in-the-loop validation for low-confidence matches

**Phase 3: Client Product Matching**
- Match scraped products to client's pharmaceutical catalog
- Identify direct competitors and similar products
- Track competitive positioning

## Project Structure

```
pharma-intelligence/
├── scrapers/
│   ├── farma_oliva.py        # Farma Oliva crawler
│   ├── punto_farma.py         # Punto Farma crawler
│   ├── farma_center.py        # Farma Center crawler
│   ├── farmacia_catedral.py   # Farmacia Catedral crawler
│   └── base_crawler.py        # Shared crawler logic
├── matching/
│   ├── barcode_matcher.py     # Barcode-based matching
│   ├── ai_matcher.py          # AI similarity matching
│   └── client_matcher.py      # Client catalog matching
├── storage/
│   ├── supabase_loader.py     # Supabase data loader
│   ├── schema.sql             # Supabase table schemas
│   └── bigquery_sync.py       # Optional: Sync Supabase → BigQuery
├── utils/
│   ├── config.py              # Configuration management
│   └── logger.py              # Logging utilities
├── tests/
│   └── ...                    # Unit and integration tests
├── .github/
│   └── workflows/
│       └── scrape.yml         # GitHub Actions workflow (if used)
├── docs/                      # Crawlee documentation (reference)
├── requirements.txt           # Python dependencies
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## Installation

### Prerequisites

- Python 3.11+
- pip or uv package manager
- Supabase account (free tier: https://supabase.com)
- Google Cloud SDK (optional, for BigQuery sync)

### Setup

1. **Clone repository**
```bash
git clone <repo-url>
cd pharma-intelligence
```

2. **Install dependencies**
```bash
# Using pip
pip install -r requirements.txt

# Or using uv (recommended)
uv pip install -r requirements.txt
```

3. **Install Crawlee with all features**
```bash
pip install 'crawlee[all]'
```

4. **Install Playwright browsers** (if using PlaywrightCrawler)
```bash
playwright install
```

5. **Configure Supabase credentials**
```bash
# Get these from your Supabase project dashboard
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"
```

6. **Set environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Usage

### Running Scrapers Locally

```bash
# Run all scrapers
python -m scrapers.run_all

# Run specific scraper
python -m scrapers.farma_oliva
```

### Running on Apify

```bash
# Deploy to Apify
apify push

# Run actor
apify call
```

### Running via GitHub Actions

Push to main branch or trigger manually:
```bash
gh workflow run scrape.yml
```

## Development

### Testing a Single Pharmacy

Start with one pharmacy website to establish the scraping pattern:

```python
import asyncio
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

async def main() -> None:
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=50,  # Limit during development
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        context.log.info(f'Processing {context.request.url}')

        # Extract product data
        product = {
            'site_code': await context.page.locator('.product-code').text_content(),
            'barcode': await context.page.locator('.barcode').text_content(),
            'name': await context.page.locator('.product-name').text_content(),
            'brand': await context.page.locator('.brand').text_content(),
            'description': await context.page.locator('.description').text_content(),
            'category': await context.page.locator('.category').text_content(),
            'price': await context.page.locator('.price').text_content(),
            'original_price': await context.page.locator('.original-price').text_content(),
            'bank_discount_price': await context.page.locator('.bank-price').text_content(),
            'bank_discount_bank_name': await context.page.locator('.bank-name').text_content(),
            'requires_prescription': await context.page.locator('.prescription-required').is_visible(),
            'payment_methods': await context.page.locator('.payment-methods').text_content(),
            'shipping_options': await context.page.locator('.shipping').text_content(),
            # ... other fields
        }

        await context.push_data(product)
        await context.enqueue_links()

    await crawler.run(['https://www.farmaoliva.com.py/'])

if __name__ == '__main__':
    asyncio.run(main())
```

### Best Practices

- **Respect robots.txt** and rate limiting
- **Add delays** between requests to avoid overwhelming servers
- **Handle errors gracefully** with retry logic (built into Crawlee)
- **Log extensively** for debugging scraping issues
- **Validate data** before loading to BigQuery
- **Version control schemas** as requirements evolve

## Monitoring & Maintenance

- Track scraping success rates and failures
- Monitor for website structure changes (breaks scrapers)
- Validate data quality (missing barcodes, price anomalies)
- Review AI matching accuracy periodically

## Roadmap

**Phase 1: Foundation**
- [ ] Setup Supabase database and schema
- [ ] Build first scraper (Farma Oliva)
- [ ] Test scraper and Supabase integration

**Phase 2: Scraper Development**
- [ ] Complete scrapers for all 4 pharmacies
- [ ] Implement error handling and retry logic
- [ ] Product data validation

**Phase 3: Product Matching**
- [ ] Barcode-based product matching
- [ ] AI-powered similarity matching
- [ ] Client catalog integration

**Phase 4: Analytics & Visualization**
- [ ] Supabase → BigQuery sync (optional)
- [ ] dbt transformations
- [ ] Looker Studio dashboards

**Phase 5: Automation**
- [ ] Automated scheduling (Apify or GitHub Actions)
- [ ] Alert system for price changes
- [ ] Monitoring and logging

## Resources

- [Crawlee Python Documentation](https://crawlee.dev/python/)
- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Python Client](https://supabase.com/docs/reference/python/introduction)
- [Apify Platform Docs](https://docs.apify.com/)
- [BigQuery Python Client](https://cloud.google.com/python/docs/reference/bigquery/latest) (optional)
- [dbt Documentation](https://docs.getdbt.com/)

## License

[Specify license]

## Contact

[Project maintainer contact information]
