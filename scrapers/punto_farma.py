"""Punto Farma scraper for pharmaceutical products - 2-PHASE APPROACH.

Phase 1: Collect all product URLs by clicking through all pages
Phase 2: Scrape each URL from database where product_name IS NULL or scraped_at < today
"""

import asyncio
import re
import sys
from datetime import datetime, date, timedelta
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

# Global db_loader instance
db_loader_instance = None


class PuntoFarmaProduct:
    """Data class for Punto Farma product extraction."""

    @staticmethod
    def extract_from_html(html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract product data from Punto Farma product page HTML.

        Args:
            html: HTML content of product page
            url: Product URL

        Returns:
            Dictionary with product data, or None if extraction fails
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Product name (h1)
            product_name_elem = soup.select_one("h1")
            product_name = product_name_elem.get_text(strip=True) if product_name_elem else None

            if not product_name:
                logger.warning(f"No product name found for {url}")
                return None

            # Site code and barcode from codigo div
            site_code = None
            barcode = None
            codigo_div = soup.select_one(".codigo")
            if codigo_div:
                # Site code: "Código: 139212"
                code_span = codigo_div.select_one("span.fw-bold.user-select-all")
                if code_span:
                    site_code = code_span.get_text(strip=True)

                # Barcode: last span with user-select-all
                barcode_spans = codigo_div.select("span.user-select-all")
                if len(barcode_spans) > 1:
                    barcode = barcode_spans[-1].get_text(strip=True)

            # Category from breadcrumb
            category_path = []
            main_category = None
            breadcrumb_links = soup.select("a.breadcrumb-item")
            for link in breadcrumb_links:
                category_text = link.get_text(strip=True)
                if category_text:
                    category_path.append(category_text)

            if category_path:
                main_category = category_path[0]

            # Prices
            current_price = None
            original_price = None
            discount_percentage = None
            discount_amount = None

            # Discounted price: "Gs. 46.166"
            discounted_price_elem = soup.select_one(".precio-con-descuento span.precio-lg")
            if discounted_price_elem:
                price_text = discounted_price_elem.get_text(strip=True)
                # Remove "Gs." and dots, extract number
                price_match = re.search(r"[\d.]+", price_text.replace(".", ""))
                if price_match:
                    current_price = float(price_match.group())

            # Regular price: "Gs. 56.300"
            regular_price_elem = soup.select_one(".precio-regular del.precio-sin-descuento")
            if regular_price_elem:
                price_text = regular_price_elem.get_text(strip=True)
                price_match = re.search(r"[\d.]+", price_text.replace(".", ""))
                if price_match:
                    original_price = float(price_match.group())

            # Discount percentage: "-18% de descuento"
            discount_elem = soup.select_one(".precio-regular div[style*='background-color']")
            if discount_elem:
                discount_text = discount_elem.get_text(strip=True)
                discount_match = re.search(r"-?(\d+)%", discount_text)
                if discount_match:
                    discount_percentage = float(discount_match.group(1))

            # Calculate discount amount if we have both prices
            if current_price and original_price:
                discount_amount = original_price - current_price
                # Recalculate percentage if not found
                if not discount_percentage:
                    discount_percentage = round((discount_amount / original_price) * 100, 2)

            # If no discounted price, use regular price as current price
            if not current_price and original_price:
                current_price = original_price
                original_price = None

            # Image URL
            image_url = None
            image_elem = soup.select_one("img[alt*='miniatura']")
            if image_elem:
                image_url = image_elem.get("src")

            # Brand from category link
            brand = None
            brand_elem = soup.select_one("div > a.category[href*='/marca/']")
            if brand_elem:
                brand = brand_elem.get_text(strip=True)

            # Product description from accordion body
            product_description = None
            desc_elem = soup.select_one(".atributos_body__wyXR6.accordion-body")
            if desc_elem:
                product_description = desc_elem.get_text(strip=True)

            # Bank discount (Itaú QR Débito)
            bank_discount_price = None
            bank_discount_bank_name = None
            bank_payment_offers = None

            # Look for bank discount section: <h6>Con Itau QR Debito</h6> and price
            bank_section = soup.find("h6", string=re.compile(r"Con\s+Itau", re.IGNORECASE))
            if bank_section:
                # Extract bank name from heading: "Con Itau QR Debito"
                bank_text = bank_section.get_text(strip=True)
                bank_match = re.search(r"Con\s+(.+?)(?:\s+\*|$)", bank_text, re.IGNORECASE)
                if bank_match:
                    bank_discount_bank_name = bank_match.group(1).strip()

                # Find the price in the same container
                container = bank_section.find_parent("div", class_="d-flex")
                if container:
                    price_span = container.find("span", class_="fs-5")
                    if price_span:
                        price_text = price_span.get_text(strip=True)
                        # Extract price: "Gs. 8.640"
                        price_match = re.search(r"Gs\.\s*([\d.,]+)", price_text)
                        if price_match:
                            bank_discount_price = float(price_match.group(1).replace(".", "").replace(",", ""))

                # Build bank payment offers description
                if bank_discount_bank_name:
                    bank_payment_offers = f"Descuento exclusivo con {bank_discount_bank_name}"

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
                "bank_discount_price": bank_discount_price,
                "bank_discount_bank_name": bank_discount_bank_name,
                "bank_payment_offers": bank_payment_offers,
                "requires_prescription": False,  # Not shown on page
                "prescription_type": None,
                "payment_methods": None,
                "shipping_options": None,
                "image_url": image_url,
                "image_urls": [image_url] if image_url else [],
                "pharmacy_source": "punto_farma",
                "product_url": url,
            }

            logger.debug(f"Extracted product: {product_name} (code: {site_code}, barcode: {barcode})")
            return product_data

        except Exception as e:
            logger.error(f"Error extracting product from {url}: {e}")
            return None


# ==============================================================================
# PHASE 1: URL COLLECTION
# ==============================================================================

@router.handler("url_collection")
async def collect_urls(context: PlaywrightCrawlingContext) -> None:
    """Phase 1: Click and save URLs after EACH page load."""
    url = context.request.url
    logger.info(f"Collecting URLs from: {url}")

    try:
        # Wait for product grid to load
        await context.page.wait_for_selector("a[href*='/producto/']", timeout=10000)

        base_url = PHARMACY_URLS["punto_farma"]["base_url"]
        max_clicks = 600  # Safety limit (~520 expected)

        clicks = 0
        no_button_count = 0
        seen_urls = set()  # Track URLs we've already processed

        logger.info("Starting URL collection...")

        while clicks < max_clicks:
            # Extract current page URLs
            product_links = await context.page.locator("a[href*='/producto/']").all()

            urls_to_insert = []
            for link in product_links:
                href = await link.get_attribute("href")
                if href:
                    if not href.startswith("http"):
                        href = f"{base_url}{href}" if href.startswith("/") else f"{base_url}/{href}"

                    # Skip if already seen (deduplicates within page and across pages)
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    site_code = None
                    url_match = re.search(r"/producto/(\d+)/", href)
                    if url_match:
                        site_code = url_match.group(1)

                    urls_to_insert.append({
                        "pharmacy_source": "punto_farma",
                        "product_url": href,
                        "site_code": site_code,
                    })

            # Save new URLs to database
            global db_loader_instance
            if db_loader_instance and urls_to_insert:
                inserted = await db_loader_instance.insert_product_urls(urls_to_insert)
                logger.info(f"Page {clicks + 1}: Found {len(urls_to_insert)} new URLs, saved {inserted}")

            # Click "Cargar más"
            load_more_button = context.page.locator("button.btn.btn-primary:has-text('Cargar más')").first

            try:
                button_visible = await load_more_button.is_visible()
            except:
                no_button_count += 1
                if no_button_count >= 3:
                    logger.info(f"Button check failed after {clicks} clicks, finishing")
                    break
                await context.page.wait_for_timeout(500)
                continue

            if button_visible:
                no_button_count = 0
                await load_more_button.click()
                clicks += 1
                await context.page.wait_for_timeout(500)  # Increased from 300ms to 500ms
            else:
                no_button_count += 1
                if no_button_count >= 3:
                    logger.info(f"No more 'Cargar más' button after {clicks} clicks")
                    break
                await context.page.wait_for_timeout(500)

        logger.info(f"Finished: {clicks} clicks, {len(seen_urls)} total unique URLs collected")

    except Exception as e:
        logger.error(f"Error collecting URLs from {url}: {e}")


# ==============================================================================
# PHASE 2: PRODUCT SCRAPING
# ==============================================================================

@router.handler("product_detail")
async def scrape_product(context: PlaywrightCrawlingContext) -> None:
    """Phase 2: Scrape product detail page and UPDATE database record."""
    logger.info(f"Scraping product: {context.request.url}")

    try:
        # Wait for product name to load
        await context.page.wait_for_selector("h1", timeout=10000)
        await context.page.wait_for_timeout(1000)

        # Get page HTML
        html = await context.page.content()

        # Extract product data
        product_data = PuntoFarmaProduct.extract_from_html(html, context.request.url)

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

async def main() -> None:
    """Run Punto Farma scraper."""
    global db_loader_instance

    settings = get_settings()
    base_url = PHARMACY_URLS["punto_farma"]["base_url"]

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

    # Check command line argument for phase
    phase = sys.argv[1] if len(sys.argv) > 1 else "phase1"

    if phase == "phase1":
        # ============================================================
        # PHASE 1: COLLECT ALL PRODUCT URLS
        # ============================================================
        logger.info("=" * 80)
        logger.info("PHASE 1: Collecting product URLs from all pages")
        logger.info("=" * 80)

        run_id = await db_loader.start_scraping_run("punto_farma_urls", "medicamentos+nutricion")

        try:
            crawler = PlaywrightCrawler(
                request_handler=router,
                proxy_configuration=proxy_configuration,
                max_requests_per_crawl=10,  # Just 2 category pages (not product pages)
                max_request_retries=2,
                request_handler_timeout=timedelta(hours=4),  # 4 hours for clicking through all pages
                headless=True,
            )

            start_urls = [
                f"{base_url}/categoria/1/medicamentos",
                f"{base_url}/categoria/238/nutricion-y-deporte",
            ]

            logger.info(f"Starting URL collection from: {start_urls}")

            await crawler.run([
                Request.from_url(url, label="url_collection") for url in start_urls
            ])

            await db_loader.complete_scraping_run(run_id, 0, 0)
            logger.info("=" * 80)
            logger.info("PHASE 1 COMPLETE!")
            logger.info("Run Phase 2 to scrape products:")
            logger.info("  python -m scrapers.punto_farma phase2")
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

        # Get URLs to scrape (product_name IS NULL or scraped_at < today)
        urls_to_scrape = await db_loader.get_urls_to_scrape("punto_farma")
        logger.info(f"Found {len(urls_to_scrape)} URLs to scrape")

        if not urls_to_scrape:
            logger.info("No URLs to scrape! Run phase1 first or all products already scraped today.")
            return

        run_id = await db_loader.start_scraping_run("punto_farma", f"phase2_{len(urls_to_scrape)}_products")

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
