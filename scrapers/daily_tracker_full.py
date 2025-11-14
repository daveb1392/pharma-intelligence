"""
Daily barcode tracker using full scraper extraction logic.
Orchestrates existing scrapers to extract complete product data from tracked URLs.
"""

import asyncio
from datetime import datetime, timedelta
from crawlee import ConcurrencySettings
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from storage.supabase_loader import SupabaseLoader
from utils.logger import get_logger

# Import extraction classes from original scrapers
from scrapers.farma_oliva import FarmaOlivaProduct
from scrapers.punto_farma import PuntoFarmaProduct
from scrapers.farmacia_center import FarmaciaCenterProduct
from scrapers.farmacia_catedral import FarmaciaCatedralProduct

logger = get_logger()


async def get_daily_tracking_urls(loader: SupabaseLoader) -> dict:
    """
    Get URLs from barcode_tracking_urls table.

    Returns:
        Dict with pharmacy_source as keys, list of URLs as values
    """
    logger.info("Fetching URLs from barcode_tracking_urls table...")

    try:
        response = loader.client.table("barcode_tracking_urls").select(
            "pharmacy_source, product_url, site_code, barcode"
        ).execute()

        urls = response.data if response.data else []
        logger.info(f"Found {len(urls)} URLs to track")

        # Group by pharmacy
        by_pharmacy = {}
        for url_record in urls:
            pharmacy = url_record["pharmacy_source"]
            if pharmacy not in by_pharmacy:
                by_pharmacy[pharmacy] = []

            by_pharmacy[pharmacy].append({
                "url": url_record["product_url"],
                "site_code": url_record.get("site_code"),
                "barcode": url_record.get("barcode"),
            })

        # Log summary
        for pharmacy, urls_list in by_pharmacy.items():
            logger.info(f"  {pharmacy}: {len(urls_list)} URLs")

        return by_pharmacy

    except Exception as e:
        logger.error(f"Error fetching URLs: {e}")
        return {}


# ============================================================================
# HANDLER WRAPPERS (use original extraction logic)
# ============================================================================

async def scrape_farma_oliva(context: PlaywrightCrawlingContext, loader: SupabaseLoader, product_info: dict):
    """Scrape Farma Oliva using original extraction class."""
    page = context.page
    url = context.request.url

    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        content = await page.content()

        # Use original extraction class
        product_data = FarmaOlivaProduct.extract_from_html(content, url)

        if product_data:
            product_id = await loader.upsert_product(product_data)

            # Insert daily snapshot
            if product_id:
                product_data["id"] = product_id
                await loader.insert_barcode_snapshot(product_data)

            name = product_data.get("product_name")
            price = product_data.get("current_price")
            logger.info(f"✓ {name} - ₲{price:,.0f}" if price else f"✓ {name}")
        else:
            logger.warning(f"Failed to extract product data from {url}")

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")


async def scrape_punto_farma(context: PlaywrightCrawlingContext, loader: SupabaseLoader, product_info: dict):
    """Scrape Punto Farma using original extraction class."""
    page = context.page
    url = context.request.url

    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        content = await page.content()

        # Use original extraction class
        product_data = PuntoFarmaProduct.extract_from_html(content, url)

        if product_data:
            product_id = await loader.upsert_product(product_data)

            # Insert daily snapshot
            if product_id:
                product_data["id"] = product_id
                await loader.insert_barcode_snapshot(product_data)

            name = product_data.get("product_name")
            price = product_data.get("current_price")
            logger.info(f"✓ {name} - ₲{price:,.0f}" if price else f"✓ {name}")
        else:
            logger.warning(f"Failed to extract product data from {url}")

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")


async def scrape_farmacia_center(context: PlaywrightCrawlingContext, loader: SupabaseLoader, product_info: dict):
    """Scrape Farmacia Center using original extraction class."""
    page = context.page
    url = context.request.url

    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        content = await page.content()

        # Use original extraction class
        product_data = FarmaciaCenterProduct.extract_from_html(content, url)

        if product_data:
            product_id = await loader.upsert_product(product_data)

            # Insert daily snapshot
            if product_id:
                product_data["id"] = product_id
                await loader.insert_barcode_snapshot(product_data)

            name = product_data.get("product_name")
            price = product_data.get("current_price")
            logger.info(f"✓ {name} - ₲{price:,.0f}" if price else f"✓ {name}")
        else:
            logger.warning(f"Failed to extract product data from {url}")

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")


async def scrape_farmacia_catedral(context: PlaywrightCrawlingContext, loader: SupabaseLoader, product_info: dict):
    """Scrape Farmacia Catedral using original extraction class."""
    page = context.page
    url = context.request.url

    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        content = await page.content()

        # Use original extraction class
        product_data = FarmaciaCatedralProduct.extract_from_html(content, url)

        if product_data:
            product_id = await loader.upsert_product(product_data)

            # Insert daily snapshot
            if product_id:
                product_data["id"] = product_id
                await loader.insert_barcode_snapshot(product_data)

            name = product_data.get("product_name")
            price = product_data.get("current_price")
            logger.info(f"✓ {name} - ₲{price:,.0f}" if price else f"✓ {name}")
        else:
            logger.warning(f"Failed to extract product data from {url}")

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")


# ============================================================================
# MAIN SCRAPER
# ============================================================================

async def scrape_pharmacy(pharmacy: str, urls_list: list, loader: SupabaseLoader):
    """Scrape products for a specific pharmacy using original extraction logic."""
    if not urls_list:
        logger.info(f"No URLs to scrape for {pharmacy}")
        return

    logger.info(f"\n{'='*60}")
    logger.info(f"Scraping {pharmacy.upper()} - {len(urls_list)} products")
    logger.info(f"{'='*60}\n")

    # Map pharmacy to handler
    handlers = {
        "farma_oliva": scrape_farma_oliva,
        "punto_farma": scrape_punto_farma,
        "farma_center": scrape_farmacia_center,  # Note: DB uses "farma_center"
        "farmacia_center": scrape_farmacia_center,  # Support both names
        "farmacia_catedral": scrape_farmacia_catedral,
    }

    handler = handlers.get(pharmacy)
    if not handler:
        logger.error(f"No handler for {pharmacy}")
        return

    # Create product info lookup
    product_lookup = {p["url"]: p for p in urls_list}

    # Define request handler
    async def request_handler(context: PlaywrightCrawlingContext):
        url = context.request.url
        product_info = product_lookup.get(url, {})
        await handler(context, loader, product_info)

    # Configure crawler - moderate concurrency for stability
    concurrency_settings = ConcurrencySettings(
        max_concurrency=10,
        min_concurrency=1,
        desired_concurrency=10,
    )

    crawler = PlaywrightCrawler(
        concurrency_settings=concurrency_settings,
        request_handler=request_handler,
        request_handler_timeout=timedelta(seconds=45),
        max_request_retries=3,
        headless=True,
        browser_type="chromium",
    )

    # Add URLs
    urls = [p["url"] for p in urls_list]
    await crawler.run(urls)

    logger.info(f"✅ Completed {pharmacy}")


async def main():
    """Main entry point for daily tracker with full extraction."""
    import os

    start_time = datetime.now()
    logger.info(f"\n{'='*60}")
    logger.info(f"DAILY BARCODE TRACKER (FULL EXTRACTION) - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}\n")

    loader = SupabaseLoader()

    # Get URLs marked for daily tracking
    urls_by_pharmacy = await get_daily_tracking_urls(loader)

    if not urls_by_pharmacy:
        logger.warning("No URLs in barcode_tracking_urls table!")
        logger.info("Run scripts/populate_tracking_urls.py first to populate URLs")
        return

    # Check if filtering by pharmacy (for parallel execution)
    pharmacy_filter = os.getenv("PHARMACY_FILTER")
    if pharmacy_filter:
        logger.info(f"Filtering to pharmacy: {pharmacy_filter}")
        if pharmacy_filter in urls_by_pharmacy:
            urls_by_pharmacy = {pharmacy_filter: urls_by_pharmacy[pharmacy_filter]}
        else:
            logger.warning(f"No URLs found for {pharmacy_filter}")
            return

    # Scrape each pharmacy
    for pharmacy, urls_list in urls_by_pharmacy.items():
        await scrape_pharmacy(pharmacy, urls_list, loader)

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    total_products = sum(len(urls) for urls in urls_by_pharmacy.values())

    logger.info(f"\n{'='*60}")
    logger.info(f"COMPLETED")
    logger.info(f"{'='*60}")
    logger.info(f"Duration: {duration:.1f}s")
    logger.info(f"Products scraped: {total_products}")
    logger.info(f"Pharmacies: {len(urls_by_pharmacy)}")
    logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
