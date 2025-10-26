"""Farmacia Center scraper for pharmaceutical products - 2-PHASE APPROACH.

Phase 1: Scroll and save all product URLs to database
Phase 2: Scrape each URL from database
"""

import asyncio
import json
import re
import sys
from datetime import timedelta
from typing import Any, Dict, List, Optional
from crawlee import Request
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from crawlee.proxy_configuration import ProxyConfiguration
from crawlee.router import Router
from bs4 import BeautifulSoup
from utils.config import get_settings, PHARMACY_URLS
from utils.logger import setup_logger, get_logger
from storage.supabase_loader import SupabaseLoader

# Setup logger
setup_logger()
logger = get_logger()

# Create router for handling different page types
router = Router()

# Global db_loader instance (will be set in main())
db_loader_instance = None


class FarmaciaCenterProduct:
    """Data class for Farmacia Center product extraction."""

    @staticmethod
    def extract_from_html(html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract product data from Farmacia Center product page HTML.

        Args:
            html: HTML content of product page
            url: Product URL

        Returns:
            Dictionary with product data, or None if extraction fails
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Extract JSON data from hidden input (most reliable source)
            json_data = None
            json_input = soup.find("input", class_="json", type="hidden")
            if json_input:
                json_value = json_input.get("value", "")
                if json_value:
                    try:
                        # The value is HTML-escaped JSON, BeautifulSoup already decodes it
                        json_data = json.loads(json_value)
                        logger.debug(f"Found JSON data for product")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON data: {e}")

            # Extract Microdata (schema.org/Product) from hidden div
            microdata = soup.find("div", attrs={"itemtype": "http://schema.org/Product"})
            if microdata:
                logger.debug(f"Found Microdata for Product")

            # Product name (priority: JSON > Microdata > h1.tit)
            product_name = None
            if json_data and "producto" in json_data:
                product_name = json_data["producto"].get("nombre")

            if not product_name and microdata:
                name_elem = microdata.find(attrs={"itemprop": "name"})
                if name_elem:
                    product_name = name_elem.get_text(strip=True)

            if not product_name:
                product_name_elem = soup.select_one("h1.tit")
                product_name = product_name_elem.get_text(strip=True) if product_name_elem else None

            if not product_name:
                logger.warning(f"No product name found for {url}")
                return None

            # Site code and barcode
            site_code = None
            barcode = None

            # From Microdata: <span itemprop="sku">1002677810026778</span>
            if microdata:
                sku_elem = microdata.find(attrs={"itemprop": "sku"})
                if sku_elem:
                    sku_text = sku_elem.get_text(strip=True)
                    # SKU format: "1002677810026778" (site_code + barcode concatenated)
                    # Based on the description pattern in microdata, it's sitecode-barcode
                    # But in SKU it's concatenated. Let's check .cod div for split version
                    site_code = sku_text

            # From HTML: .cod div: "10030348-7703281002468" (more reliable for split)
            cod_div = soup.select_one(".cod")
            if cod_div:
                cod_text = cod_div.get_text(strip=True)
                # Split on hyphen: first part is site_code, second is barcode
                parts = cod_text.split("-")
                if len(parts) == 2:
                    site_code = parts[0].strip()
                    barcode = parts[1].strip()
                elif len(parts) == 1 and not site_code:
                    site_code = parts[0].strip()

            # Brand (priority: JSON > Microdata > data-tit)
            brand = None
            if json_data and "producto" in json_data:
                brand = json_data["producto"].get("marca")

            if not brand and microdata:
                brand_elem = microdata.find(attrs={"itemprop": "brand"})
                if brand_elem:
                    brand = brand_elem.get_text(strip=True)

            # Fallback to data-tit attribute: "Medicamentos ABBOTT "
            if not brand:
                central_div = soup.select_one("#central[data-tit]")
                if central_div:
                    data_tit = central_div.get("data-tit", "")
                    # Extract brand from "Medicamentos ABBOTT " or similar
                    match = re.search(r"(?:Medicamentos|Suplementos)\s+(.+)", data_tit, re.IGNORECASE)
                    if match:
                        brand = match.group(1).strip()

            # Category (priority: JSON > data-tit)
            category_path = []
            main_category = None
            if json_data and "producto" in json_data:
                categoria = json_data["producto"].get("categoria", "")
                if categoria:
                    # Parse "Medicamentos > Vitaminas y minerales > Vitaminas D"
                    category_path = [cat.strip() for cat in categoria.split(">")]
                    if category_path:
                        main_category = category_path[0]

            # Fallback to data-tit
            if not main_category:
                central_div = soup.select_one("#central[data-tit]")
                if central_div:
                    data_tit = central_div.get("data-tit", "")
                    if data_tit:
                        # First word is the category: "Medicamentos" or "Suplementos"
                        category_match = re.match(r"^(\w+)", data_tit)
                        if category_match:
                            main_category = category_match.group(1)
                            category_path = [main_category]

            # Description (from Microdata or HTML)
            product_description = None
            if microdata:
                desc_elem = microdata.find(attrs={"itemprop": "description"})
                if desc_elem:
                    product_description = desc_elem.get_text(strip=True)

            # Fallback to HTML: <div class="desc"><p>...</p></div>
            if not product_description:
                desc_div = soup.select_one(".desc p")
                if desc_div:
                    product_description = desc_div.get_text(strip=True)

            # Prices: <div class="precios">
            current_price = None
            original_price = None
            discount_percentage = None
            discount_amount = None

            # Original price (lista): <del class="precio lista"><span class="monto">230.000</span></del>
            original_price_elem = soup.select_one(".precios del.precio.lista .monto")
            if original_price_elem:
                price_text = original_price_elem.get_text(strip=True)
                # Remove dots and convert to float
                price_clean = price_text.replace(".", "").replace(",", "")
                if price_clean.isdigit():
                    original_price = float(price_clean)

            # Current price (venta): <strong class="precio venta"><span class="monto">193.200</span></strong>
            current_price_elem = soup.select_one(".precios strong.precio.venta .monto")
            if current_price_elem:
                price_text = current_price_elem.get_text(strip=True)
                price_clean = price_text.replace(".", "").replace(",", "")
                if price_clean.isdigit():
                    current_price = float(price_clean)

            # Calculate discount if both prices exist
            if current_price and original_price:
                discount_amount = original_price - current_price
                discount_percentage = round((discount_amount / original_price) * 100, 2)

            # If no original price (no discount), use current price
            if not current_price and original_price:
                current_price = original_price
                original_price = None

            # Image URL: <img loading="lazy" data-src-g="..." src="..." alt="...">
            image_url = None
            image_elem = soup.select_one("img[alt]")
            if image_elem:
                # Prefer data-src-g, fallback to src
                image_url = image_elem.get("data-src-g") or image_elem.get("src")
                if image_url and not image_url.startswith("http"):
                    image_url = f"https:{image_url}" if image_url.startswith("//") else None

            # Build product dictionary
            product_data = {
                "site_code": site_code,
                "barcode": barcode,
                "product_name": product_name,
                "brand": brand,
                "product_description": product_description,
                "product_details": {},
                "category_path": category_path,
                "main_category": main_category,
                "current_price": current_price,
                "original_price": original_price,
                "discount_percentage": discount_percentage,
                "discount_amount": discount_amount,
                "bank_discount_price": None,
                "bank_discount_bank_name": None,
                "bank_payment_offers": None,
                "requires_prescription": False,  # Not visible on page
                "prescription_type": None,
                "payment_methods": None,
                "shipping_options": None,
                "image_url": image_url,
                "image_urls": [image_url] if image_url else [],
                "pharmacy_source": "farma_center",
                "product_url": url,
            }

            logger.debug(f"Extracted product: {product_name} (code: {site_code}, barcode: {barcode})")
            logger.debug(f"Brand: {brand}, Category: {main_category}, Description: {product_description[:50] if product_description else None}")
            return product_data

        except Exception as e:
            logger.error(f"Error extracting product from {url}: {e}")
            return None


# ==============================================================================
# PHASE 1: URL COLLECTION
# ==============================================================================

@router.handler("url_collection")
async def collect_urls(context: PlaywrightCrawlingContext) -> None:
    """Phase 1: Scroll and save all product URLs to database."""
    logger.info(f"Collecting URLs from: {context.request.url}")

    try:
        # Wait for products to load
        await context.page.wait_for_selector("a[href*='/catalogo/']", timeout=10000)
        await context.page.wait_for_timeout(1000)

        # Lazy scroll to load all products
        logger.info("Starting lazy scroll to load all 4,199 products...")

        base_url = PHARMACY_URLS["farma_center"]["base_url"]
        previous_height = 0
        scroll_attempts = 0
        no_change_count = 0
        max_scroll_attempts = 1000  # Increased for 4,199 products
        max_no_change = 15  # Wait for 15 consecutive scrolls with no change (15 * 3sec = 45sec patience)
        seen_urls = set()  # Track URLs we've already processed

        while scroll_attempts < max_scroll_attempts:
            # Extract product links from current view and save immediately
            product_links = await context.page.locator("a[href*='/catalogo/']").all()

            urls_to_insert = []
            for link in product_links:
                href = await link.get_attribute("href")
                if href:
                    # Convert to absolute URL if needed
                    if not href.startswith("http"):
                        href = f"{base_url}{href}" if href.startswith("/") else f"{base_url}/{href}"

                    # Skip if already seen
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    # Extract site_code from URL: /catalogo/10026778-...
                    site_code = None
                    url_match = re.search(r"/catalogo/(\d+)-", href)
                    if url_match:
                        site_code = url_match.group(1)

                    urls_to_insert.append({
                        "pharmacy_source": "farma_center",
                        "product_url": href,
                        "site_code": site_code,
                    })

            # Save new URLs to database
            global db_loader_instance
            if db_loader_instance and urls_to_insert:
                inserted = await db_loader_instance.insert_product_urls(urls_to_insert)
                logger.info(f"Scroll {scroll_attempts + 1}: Found {len(urls_to_insert)} new URLs, saved {inserted}")

            # Scroll to bottom
            await context.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await context.page.wait_for_timeout(3000)  # 3 seconds delay for slow page loading

            # Get new scroll height
            current_height = await context.page.evaluate("document.body.scrollHeight")

            # Check if we've reached the bottom
            if current_height == previous_height:
                no_change_count += 1
                logger.debug(f"No height change ({no_change_count}/{max_no_change})")
                if no_change_count >= max_no_change:
                    logger.info(f"Reached bottom after {scroll_attempts} scrolls")
                    break
            else:
                no_change_count = 0

            previous_height = current_height
            scroll_attempts += 1

            if scroll_attempts % 10 == 0:
                logger.info(f"Progress: {len(seen_urls)} total unique URLs collected so far")

        logger.info(f"Finished: {scroll_attempts} scrolls, {len(seen_urls)} total unique URLs collected")

    except Exception as e:
        logger.error(f"Error collecting URLs from {context.request.url}: {e}")


# ==============================================================================
# PHASE 2: PRODUCT SCRAPING
# ==============================================================================

@router.handler("product_detail")
async def scrape_product(context: PlaywrightCrawlingContext) -> None:
    """Phase 2: Scrape product detail page and UPDATE database record."""
    logger.info(f"Scraping product: {context.request.url}")

    try:
        # Wait for product name to load
        await context.page.wait_for_selector("h1.tit", timeout=10000)
        await context.page.wait_for_timeout(1000)

        # Get page HTML
        html = await context.page.content()

        # Extract product data
        product_data = FarmaciaCenterProduct.extract_from_html(html, context.request.url)

        if product_data:
            # Update database record (upsert based on pharmacy_source + product_url)
            global db_loader_instance
            if db_loader_instance:
                product_id = await db_loader_instance.upsert_product(product_data)
                if product_id:
                    logger.info(f"Saved: {product_data['product_name']}")
                else:
                    logger.warning(f"Failed to save: {product_data['product_name']}")
            else:
                logger.info(f"No DB loader: {product_data['product_name']}")
        else:
            logger.warning(f"Failed to extract product from {context.request.url}")

    except Exception as e:
        logger.error(f"Error scraping product {context.request.url}: {e}")


# ==============================================================================
# MAIN
# ==============================================================================

async def main(phase: str = None) -> None:
    """Run Farmacia Center scraper.

    Args:
        phase: Scraping phase ("phase1" or "phase2"). If None, determined from CLI args or defaults to "phase1".
    """
    global db_loader_instance

    settings = get_settings()
    base_url = PHARMACY_URLS["farma_center"]["base_url"]

    # Initialize Supabase loader
    db_loader = SupabaseLoader()
    db_loader_instance = db_loader

    # Configure proxy rotation (if proxies provided)
    proxy_configuration = None
    if settings.proxy_urls:
        proxy_list = [url.strip() for url in settings.proxy_urls.split(',') if url.strip()]
        if proxy_list:
            proxy_configuration = ProxyConfiguration(proxy_urls=proxy_list)
            logger.info(f"Using {len(proxy_list)} residential proxies for rotation")
        else:
            logger.info("No proxies configured - using direct connection")
    else:
        logger.info("No proxies configured - using direct connection")

    # Determine phase: 1) Function parameter, 2) CLI arg, 3) Default to phase1
    if phase is None:
        if len(sys.argv) > 1:
            phase = sys.argv[1]
        else:
            phase = "phase1"

    if phase == "phase1":
        # ============================================================
        # PHASE 1: COLLECT ALL PRODUCT URLS
        # ============================================================
        logger.info("=" * 80)
        logger.info("PHASE 1: Collecting product URLs from medicamentos category")
        logger.info("=" * 80)

        run_id = await db_loader.start_scraping_run("farma_center_urls", "medicamentos")

        try:
            crawler = PlaywrightCrawler(
                request_handler=router,
                proxy_configuration=proxy_configuration,
                max_requests_per_crawl=10,  # Just 1 category page
                max_request_retries=2,
                request_handler_timeout=timedelta(hours=2),  # 2 hours for scrolling through all products
                headless=True,
            )

            start_url = f"{base_url}/medicamentos"
            logger.info(f"Starting URL collection from: {start_url}")

            await crawler.run([Request.from_url(start_url, label="url_collection")])

            await db_loader.complete_scraping_run(run_id, 0, 0)
            logger.info("=" * 80)
            logger.info("PHASE 1 COMPLETE!")
            logger.info("Run Phase 2 to scrape products:")
            logger.info("  python -m scrapers.farmacia_center phase2")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            await db_loader.complete_scraping_run(run_id, 0, 0, str(e))
            raise

    elif phase == "phase2":
        # ============================================================
        # PHASE 2: SCRAPE PRODUCTS FROM DATABASE URLS
        # ============================================================
        logger.info("=" * 80)
        logger.info("PHASE 2: Scraping products from collected URLs")
        logger.info("=" * 80)

        # Get URLs to scrape
        urls_to_scrape = await db_loader.get_urls_to_scrape("farma_center")
        logger.info(f"Found {len(urls_to_scrape)} URLs to scrape")

        if not urls_to_scrape:
            logger.info("No URLs to scrape! Run phase1 first or all products already scraped today.")
            return

        run_id = await db_loader.start_scraping_run("farma_center", f"phase2_{len(urls_to_scrape)}_products")

        try:
            crawler = PlaywrightCrawler(
                request_handler=router,
                proxy_configuration=proxy_configuration,
                max_requests_per_crawl=len(urls_to_scrape) + 100,
                max_request_retries=2,
                request_handler_timeout=timedelta(seconds=30),  # 30 seconds per product page
                headless=True,
            )

            # Enqueue all product URLs
            requests = [
                Request.from_url(url, label="product_detail") for url in urls_to_scrape
            ]

            logger.info(f"Starting scraping of {len(requests)} products...")

            await crawler.run(requests)

            # Get final count
            dataset = await crawler.get_dataset()
            data = await dataset.get_data()
            total_scraped = len(data.items)

            logger.info("=" * 80)
            logger.info(f"PHASE 2 COMPLETE: {total_scraped} products scraped!")
            logger.info("=" * 80)

            await db_loader.complete_scraping_run(run_id, total_scraped, 0)

        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            await db_loader.complete_scraping_run(run_id, 0, 0, str(e))
            raise

    else:
        logger.error(f"Unknown phase: {phase}. Use 'phase1' or 'phase2'")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
