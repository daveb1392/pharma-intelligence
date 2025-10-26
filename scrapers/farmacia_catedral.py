"""Farmacia Catedral scraper for pharmaceutical products - 2-PHASE APPROACH.

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


class FarmaciaCatedralProduct:
    """Data class for Farmacia Catedral product extraction."""

    @staticmethod
    def extract_from_html(html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract product data from Farmacia Catedral product page HTML.

        Args:
            html: HTML content of product page
            url: Product URL

        Returns:
            Dictionary with product data, or None if extraction fails
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Extract JSON-LD structured data
            json_ld = None
            json_ld_script = soup.find("script", type="application/ld+json")
            if json_ld_script and json_ld_script.string:
                try:
                    json_ld = json.loads(json_ld_script.string)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON-LD for {url}: {e}")

            # Product name (from JSON-LD or fallback to h1)
            product_name = None
            if json_ld:
                product_name = json_ld.get("name")
            if not product_name:
                product_name_elem = soup.select_one("h1.title-ficha")
                product_name = product_name_elem.get_text(strip=True) if product_name_elem else None

            if not product_name:
                logger.warning(f"No product name found for {url}")
                return None

            # Site code (SKU) and barcode
            site_code = None
            barcode = None

            # From JSON-LD
            if json_ld:
                site_code = json_ld.get("sku")

            # From HTML: <p class="codigo-ficha">CÓD.: 66</p>
            if not site_code:
                codigo_elem = soup.select_one(".codigo-ficha")
                if codigo_elem:
                    codigo_text = codigo_elem.get_text(strip=True)
                    match = re.search(r"CÓD\.:?\s*(.+)", codigo_text)
                    if match:
                        site_code = match.group(1).strip()

            # Barcode: <p class="barra-ficha">CÓD. BARRAS: 7840036005616</p>
            barcode_elem = soup.select_one(".barra-ficha")
            if barcode_elem:
                barcode_text = barcode_elem.get_text(strip=True)
                match = re.search(r"CÓD\.\s*BARRAS:?\s*(.+)", barcode_text)
                if match:
                    barcode = match.group(1).strip()

            # Brand (from JSON-LD or HTML link)
            brand = None
            if json_ld and "brand" in json_ld:
                brand = json_ld["brand"].get("name")
            if not brand:
                brand_elem = soup.select_one("a.title-marca")
                brand = brand_elem.get_text(strip=True) if brand_elem else None

            # Category from breadcrumb
            category_path = []
            main_category = None
            breadcrumb_items = soup.select("ol.breadcrumb a.breadcrumb-item")
            for item in breadcrumb_items:
                category_text = item.get_text(strip=True)
                if category_text and category_text != "Inicio":
                    category_path.append(category_text)

            if category_path:
                main_category = category_path[0]

            # Description (from JSON-LD or HTML)
            product_description = None
            if json_ld:
                product_description = json_ld.get("description")

            # Full description from tab: <div id="home-tab-pane">
            full_description = None
            desc_tab = soup.select_one("#home-tab-pane")
            if desc_tab:
                full_description = desc_tab.get_text(strip=True)
                # Remove "Descripción del producto" heading (case insensitive)
                full_description = re.sub(r"^Descripción del producto\s*", "", full_description, flags=re.IGNORECASE)

            # Short description from tab: <div id="profile-tab-pane">
            short_description = None
            short_desc_tab = soup.select_one("#profile-tab-pane")
            if short_desc_tab:
                short_description = short_desc_tab.get_text(strip=True)
                # Remove "Resumen del producto" heading
                short_description = re.sub(r"^Resumen del producto\s*", "", short_description, flags=re.IGNORECASE)

            # Prefer full description, fallback to short, then JSON-LD
            if full_description:
                product_description = full_description
            elif short_description:
                product_description = short_description

            # Prices
            current_price = None
            original_price = None
            discount_percentage = None
            discount_amount = None

            # From JSON-LD
            if json_ld and "offers" in json_ld:
                offers = json_ld["offers"]
                if "price" in offers:
                    current_price = float(offers["price"])

            # From HTML: <p class="precio-web">Gs. 74.950 <span>Gs. 149.900</span></p>
            precio_web = soup.select_one(".precio-web")
            if precio_web:
                # Current price (first text node)
                precio_text = precio_web.get_text(strip=True)
                # Split to get current and original prices
                prices = re.findall(r"Gs\.\s*([\d.,]+)", precio_text)
                if len(prices) >= 1:
                    current_price = float(prices[0].replace(".", "").replace(",", ""))
                if len(prices) >= 2:
                    original_price = float(prices[1].replace(".", "").replace(",", ""))

            # Discount percentage from tag: <p class="tag-descuentos">-50%</p>
            discount_tag = soup.select_one(".tag-descuentos")
            if discount_tag:
                discount_text = discount_tag.get_text(strip=True)
                match = re.search(r"-?(\d+)%", discount_text)
                if match:
                    discount_percentage = float(match.group(1))

            # Calculate discount amount if both prices exist
            if current_price and original_price:
                discount_amount = original_price - current_price
                # Recalculate percentage if not found
                if not discount_percentage:
                    discount_percentage = round((discount_amount / original_price) * 100, 2)

            # Bank discount
            bank_discount_price = None
            bank_discount_bank_name = None
            bank_discount_percentage = None

            # Bank name from header: <h3 class="title-itau">...<img src="..." alt="Logo de Cooperativa Universitaria">
            bank_header = soup.select_one(".title-itau")
            if bank_header:
                bank_img = bank_header.select_one("img")
                if bank_img:
                    bank_alt = bank_img.get("alt", "")
                    # Extract bank name from alt text: "Logo de Cooperativa Universitaria"
                    match = re.search(r"Logo de (.+)", bank_alt)
                    if match:
                        bank_discount_bank_name = match.group(1).strip()

            # Bank discount price and percentage: <li class="text-descuento">30% en Web/Sucursal.</li> <li>Gs. 31.500</li>
            bank_list = soup.select(".list-itau li")
            for li in bank_list:
                li_text = li.get_text(strip=True)
                # Discount percentage: "30% en Web/Sucursal."
                percent_match = re.search(r"(\d+)%", li_text)
                if percent_match:
                    bank_discount_percentage = float(percent_match.group(1))
                # Price: "Gs. 31.500"
                price_match = re.search(r"Gs\.\s*([\d.,]+)", li_text)
                if price_match:
                    bank_discount_price = float(price_match.group(1).replace(".", "").replace(",", ""))

            # Bank payment offers (combined info)
            bank_payment_offers = None
            if bank_discount_bank_name or bank_discount_percentage:
                bank_payment_offers = f"{bank_discount_percentage}% descuento con {bank_discount_bank_name}" if bank_discount_bank_name else f"{bank_discount_percentage}% descuento"

            # Prescription requirement
            requires_prescription = False
            prescription_type = None
            prescription_alert = soup.select_one(".alert.alert-warning")
            if prescription_alert:
                alert_text = prescription_alert.get_text(strip=True)
                if "receta" in alert_text.lower():
                    requires_prescription = True
                    prescription_type = "Receta médica obligatoria"

            # Stock availability
            stock_available = False
            stock_elem = soup.select_one(".stock-ficha")
            if stock_elem:
                stock_text = stock_elem.get_text(strip=True)
                if "disponible" in stock_text.lower():
                    stock_available = True

            # Image URL (from JSON-LD or HTML)
            image_url = None
            if json_ld and "image" in json_ld:
                images = json_ld["image"]
                if isinstance(images, list) and len(images) > 0:
                    image_url = images[0]
            if not image_url:
                image_elem = soup.select_one("img[alt='Imagen de Producto']")
                if image_elem:
                    image_url = image_elem.get("src")

            # Build product dictionary
            product_data = {
                "site_code": site_code,
                "barcode": barcode,
                "product_name": product_name,
                "brand": brand,
                "product_description": product_description,
                "product_details": {
                    "stock_available": stock_available,
                },
                "category_path": category_path,
                "main_category": main_category,
                "current_price": current_price,
                "original_price": original_price,
                "discount_percentage": discount_percentage,
                "discount_amount": discount_amount,
                "bank_discount_price": bank_discount_price,
                "bank_discount_bank_name": bank_discount_bank_name,
                "bank_payment_offers": bank_payment_offers,
                "requires_prescription": requires_prescription,
                "prescription_type": prescription_type,
                "payment_methods": None,
                "shipping_options": None,
                "image_url": image_url,
                "image_urls": [image_url] if image_url else [],
                "pharmacy_source": "farmacia_catedral",
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
    """Phase 1: Scroll and save all product URLs to database."""
    logger.info(f"Collecting URLs from: {context.request.url}")

    try:
        # Wait for product grid to load
        await context.page.wait_for_selector("a[href*='/producto/']", timeout=10000)
        await context.page.wait_for_timeout(1000)

        # Lazy scroll to load all products (4-5K expected)
        logger.info("Starting lazy scroll to load all products (4-5K expected)...")

        base_url = PHARMACY_URLS["farmacia_catedral"]["base_url"]
        previous_height = 0
        scroll_attempts = 0
        no_change_count = 0
        max_scroll_attempts = 1000  # Increased for 4-5K products
        max_no_change = 15  # Wait for 15 consecutive scrolls with no change (15 * 3sec = 45sec patience)
        seen_urls = set()  # Track URLs we've already processed

        while scroll_attempts < max_scroll_attempts:
            # Extract product links from current view and save immediately
            product_links = await context.page.locator("a[href*='/producto/']").all()

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

                    # Extract site_code from URL: /producto/66/...
                    site_code = None
                    url_match = re.search(r"/producto/(\d+)/", href)
                    if url_match:
                        site_code = url_match.group(1)

                    urls_to_insert.append({
                        "pharmacy_source": "farmacia_catedral",
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
        await context.page.wait_for_selector("h1.title-ficha", timeout=10000)
        await context.page.wait_for_timeout(1000)

        # Get page HTML
        html = await context.page.content()

        # Extract product data
        product_data = FarmaciaCatedralProduct.extract_from_html(html, context.request.url)

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
    """Run Farmacia Catedral scraper.

    Args:
        phase: Scraping phase ("phase1" or "phase2"). If None, determined from CLI args or defaults to "phase1".
    """
    global db_loader_instance

    settings = get_settings()
    base_url = PHARMACY_URLS["farmacia_catedral"]["base_url"]

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

        run_id = await db_loader.start_scraping_run("farmacia_catedral_urls", "medicamentos")

        try:
            crawler = PlaywrightCrawler(
                request_handler=router,
                proxy_configuration=proxy_configuration,
                max_requests_per_crawl=10,  # Just 1 category page
                max_request_retries=2,
                request_handler_timeout=timedelta(hours=2),  # 2 hours for scrolling through all products
                headless=True,
            )

            # FIXED URL: Use correct medicamentos category page
            start_url = f"{base_url}/categoria/1/medicamentos?marcas=&categorias=&categorias_top=1"
            logger.info(f"Starting URL collection from: {start_url}")

            await crawler.run([Request.from_url(start_url, label="url_collection")])

            await db_loader.complete_scraping_run(run_id, 0, 0)
            logger.info("=" * 80)
            logger.info("PHASE 1 COMPLETE!")
            logger.info("Run Phase 2 to scrape products:")
            logger.info("  python -m scrapers.farmacia_catedral phase2")
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
        urls_to_scrape = await db_loader.get_urls_to_scrape("farmacia_catedral")
        logger.info(f"Found {len(urls_to_scrape)} URLs to scrape")

        if not urls_to_scrape:
            logger.info("No URLs to scrape! Run phase1 first or all products already scraped today.")
            return

        run_id = await db_loader.start_scraping_run("farmacia_catedral", f"phase2_{len(urls_to_scrape)}_products")

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
