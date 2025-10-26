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
# PHASE 1: URL COLLECTION (Using POST API)
# ==============================================================================

async def collect_urls_from_api() -> int:
    """Phase 1: Fetch product URLs from POST API and save to database.

    This uses Punto Farma's Next.js Server Action pagination API which is much
    faster than clicking through pages.

    Returns:
        Number of total URLs saved to database
    """
    import httpx
    import json

    base_url = "https://www.puntofarma.com.py"
    api_url = f"{base_url}/categoria/1/medicamentos"

    # Headers required for Next.js Server Action
    headers = {
        "accept": "text/x-component",
        "content-type": "text/plain;charset=UTF-8",
        "next-action": "48e9f2eca478537e00a58539a9f9edcf2e1dff77",
        "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22categoria%22%2C%7B%22children%22%3A%5B%221%22%2C%7B%22children%22%3A%5B%22medicamentos%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%5D%7D%5D%7D%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
        "origin": base_url,
        "referer": api_url,
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get first page to determine total products and pages
        payload = '["/productos/categoria/1?p=1&orderBy=destacado&descuento="]'
        response = await client.post(api_url, headers=headers, content=payload)

        # Parse Next.js Server Component response (format: "1:{json_data}")
        match = re.search(r'1:(\{"ok".*\})', response.text)
        if not match:
            logger.error("Failed to parse API response format")
            return 0

        data = json.loads(match.group(1))
        total_products = data.get("total", 0)
        results_per_page = len(data.get("results", []))

        if results_per_page == 0:
            logger.error("No products found in first page")
            return 0

        total_pages = (total_products + results_per_page - 1) // results_per_page

        logger.info(f"Found {total_products} total products across {total_pages} pages")

        seen_urls = set()

        # Loop through all pages
        for page in range(1, total_pages + 1):
            payload = f'["/productos/categoria/1?p={page}&orderBy=destacado&descuento="]'

            try:
                response = await client.post(api_url, headers=headers, content=payload)

                # Parse response
                match = re.search(r'1:(\{"ok".*\})', response.text)
                if not match:
                    logger.warning(f"Failed to parse page {page}")
                    continue

                page_data = json.loads(match.group(1))
                products = page_data.get("results", [])

                urls_to_insert = []
                for product in products:
                    codigo = product.get("codigo")  # Site code
                    descripcion = product.get("descripcion", "")
                    codigoBarra = product.get("codigoBarra")  # Barcode

                    if not codigo:
                        continue

                    # Build product URL (Punto Farma format: /producto/{codigo}/{slug})
                    slug = descripcion.lower().replace(' ', '-')
                    slug = re.sub(r'[^a-z0-9-]', '', slug)  # Remove special chars
                    slug = re.sub(r'-+', '-', slug)  # Replace multiple dashes
                    product_url = f"{base_url}/producto/{codigo}/{slug}"

                    if product_url in seen_urls:
                        continue
                    seen_urls.add(product_url)

                    urls_to_insert.append({
                        "pharmacy_source": "punto_farma",
                        "product_url": product_url,
                        "site_code": str(codigo),
                    })

                # Save to database
                global db_loader_instance
                if db_loader_instance and urls_to_insert:
                    inserted = await db_loader_instance.insert_product_urls(urls_to_insert)
                    logger.info(f"Page {page}/{total_pages}: Saved {inserted} URLs")

                await asyncio.sleep(0.1)  # Small delay between requests

            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                continue

        logger.info(f"Finished: {len(seen_urls)} total unique URLs collected")
        return len(seen_urls)


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

async def main(phase: str = None) -> None:
    """Run Punto Farma scraper.

    Args:
        phase: Scraping phase ("phase1" or "phase2"). If None, determined from CLI args or defaults to "phase1".
    """
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

    # Determine phase: 1) Function parameter, 2) CLI arg, 3) Default to phase1
    if phase is None:
        if len(sys.argv) > 1:
            phase = sys.argv[1]
        else:
            phase = "phase1"

    if phase == "phase1":
        # ============================================================
        # PHASE 1: COLLECT ALL PRODUCT URLS (Using POST API)
        # ============================================================
        logger.info("=" * 80)
        logger.info("PHASE 1: Collecting product URLs using POST API")
        logger.info("=" * 80)

        run_id = await db_loader.start_scraping_run("punto_farma_urls", "medicamentos_api")

        try:
            # Call the API-based URL collection function
            total_urls = await collect_urls_from_api()

            await db_loader.complete_scraping_run(run_id, 0, 0)
            logger.info("=" * 80)
            logger.info(f"PHASE 1 COMPLETE! Collected {total_urls} product URLs")
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
