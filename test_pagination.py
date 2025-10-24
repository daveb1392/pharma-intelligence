"""Test pagination discovery for Farma Oliva."""

import asyncio
from crawlee import Request
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from crawlee.router import Router
from utils.config import PHARMACY_URLS
from utils.logger import setup_logger, get_logger

setup_logger()
logger = get_logger()

router = Router()

# Track discovered pages
discovered_pages = []


@router.handler("category_listing")
async def handle_category_listing(context: PlaywrightCrawlingContext) -> None:
    """Handle category listing pages to discover next pages."""
    logger.info(f"Processing category listing: {context.request.url}")
    discovered_pages.append(context.request.url)

    try:
        # Wait for product grid to load
        await context.page.wait_for_selector(".products", timeout=10000)

        # Extract all product links (but don't enqueue them for this test)
        product_links = await context.page.locator(".product a.ecommercepro-LoopProduct-link").all()
        logger.info(f"Found {len(product_links)} products on page")

        # Check for pagination/next page
        next_button = context.page.locator("a.next.page-numbers").first
        next_count = await next_button.count()
        logger.info(f"Next button count: {next_count}")

        if next_count > 0:
            next_href = await next_button.get_attribute("href")
            logger.info(f"Next button href (raw): {next_href}")

            if next_href:
                if not next_href.startswith("http"):
                    base_url = PHARMACY_URLS["farma_oliva"]["base_url"]
                    next_href = f"{base_url}/{next_href.lstrip('/')}"

                logger.info(f"Enqueuing next page: {next_href}")
                await context.add_requests([Request.from_url(next_href, label="category_listing")])
                logger.info(f"✓ Successfully enqueued next page: {next_href}")
            else:
                logger.warning(f"Next button found but href is empty")
        else:
            logger.info(f"No next button found - this is the last page")

    except Exception as e:
        logger.error(f"Error processing category listing {context.request.url}: {e}")


async def main() -> None:
    """Run pagination test."""
    base_url = PHARMACY_URLS["farma_oliva"]["base_url"]

    # Create crawler with limit
    crawler = PlaywrightCrawler(
        request_handler=router,
        max_requests_per_crawl=50,  # Test with 50 pages
        headless=True,
    )

    # Start with medicamentos page 1
    start_url = f"{base_url}/catalogo/medicamentos-c3"

    logger.info(f"Starting pagination test from: {start_url}")
    logger.info(f"Max requests: 50 (should discover ~50 pages)")

    await crawler.run([Request.from_url(start_url, label="category_listing")])

    logger.info(f"\n{'='*60}")
    logger.info(f"PAGINATION TEST RESULTS")
    logger.info(f"{'='*60}")
    logger.info(f"Total pages discovered: {len(discovered_pages)}")
    logger.info(f"Expected: 50 pages (or 163 if no limit)")
    logger.info(f"\nFirst 5 pages:")
    for page in discovered_pages[:5]:
        logger.info(f"  {page}")
    logger.info(f"\nLast 5 pages:")
    for page in discovered_pages[-5:]:
        logger.info(f"  {page}")


if __name__ == "__main__":
    asyncio.run(main())
