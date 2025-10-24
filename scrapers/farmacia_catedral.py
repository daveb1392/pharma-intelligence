"""Farmacia Catedral scraper for pharmaceutical products."""

import asyncio
import json
import re
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

            # Short description from tab: <div id="profile-tab-pane">
            short_description = None
            short_desc_tab = soup.select_one("#profile-tab-pane")
            if short_desc_tab:
                short_description = short_desc_tab.get_text(strip=True)
                # Remove "Resumen del producto" heading
                short_description = re.sub(r"^Resumen del producto\s*", "", short_description)

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


@router.default_handler
async def handle_product_page(context: PlaywrightCrawlingContext) -> None:
    """Handle product detail pages."""
    logger.info(f"Processing product page: {context.request.url}")

    try:
        # Wait for product name to load
        await context.page.wait_for_selector("h1.title-ficha", timeout=10000)
        await context.page.wait_for_timeout(1000)

        # Get page HTML
        html = await context.page.content()

        # Extract product data
        product_data = FarmaciaCatedralProduct.extract_from_html(html, context.request.url)

        if product_data:
            # Save to dataset (Crawlee built-in storage)
            await context.push_data(product_data)

            # Save to Supabase immediately
            global db_loader_instance
            if db_loader_instance:
                product_id = await db_loader_instance.upsert_product(product_data)
                if product_id:
                    logger.info(f"Saved to Supabase: {product_data['product_name']}")
                else:
                    logger.warning(f"Failed to save to Supabase: {product_data['product_name']}")
            else:
                logger.info(f"Saved to local dataset: {product_data['product_name']}")
        else:
            logger.warning(f"Failed to extract product from {context.request.url}")

    except Exception as e:
        logger.error(f"Error processing product page {context.request.url}: {e}")


@router.handler("category_listing")
async def handle_category_listing(context: PlaywrightCrawlingContext) -> None:
    """Handle category listing pages with lazy scrolling."""
    logger.info(f"Processing category listing: {context.request.url}")

    try:
        # Wait for product grid to load
        await context.page.wait_for_selector("a[href*='/producto/']", timeout=10000)

        # Lazy scroll to load all products
        logger.info("Starting lazy scroll to load all products...")

        previous_height = 0
        scroll_attempts = 0
        max_scroll_attempts = 100  # Prevent infinite loops

        while scroll_attempts < max_scroll_attempts:
            # Scroll to bottom
            await context.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await context.page.wait_for_timeout(2000)  # Wait for lazy load

            # Get new scroll height
            current_height = await context.page.evaluate("document.body.scrollHeight")

            # Check if we've reached the bottom (no new content loaded)
            if current_height == previous_height:
                logger.info(f"Reached bottom of page after {scroll_attempts} scrolls")
                break

            previous_height = current_height
            scroll_attempts += 1

            if scroll_attempts % 5 == 0:
                logger.info(f"Scroll attempt {scroll_attempts}/{max_scroll_attempts}...")

        # Extract all product links
        product_links = await context.page.locator("a[href*='/producto/']").all()
        logger.info(f"Found {len(product_links)} product links after lazy loading")

        # Enqueue each product link
        base_url = PHARMACY_URLS["farmacia_catedral"]["base_url"]
        enqueued_urls = set()

        for link in product_links:
            href = await link.get_attribute("href")
            if href:
                # Convert relative URLs to absolute
                if not href.startswith("http"):
                    href = f"{base_url}{href}" if href.startswith("/") else f"{base_url}/{href}"

                # Avoid duplicates
                if href not in enqueued_urls:
                    await context.add_requests([Request.from_url(href, label="default")])
                    enqueued_urls.add(href)
                    logger.debug(f"Enqueued product: {href}")

        logger.info(f"Enqueued {len(enqueued_urls)} unique product URLs")

    except Exception as e:
        logger.error(f"Error processing category listing {context.request.url}: {e}")


async def main() -> None:
    """Run Farmacia Catedral scraper."""
    global db_loader_instance

    settings = get_settings()
    base_url = PHARMACY_URLS["farmacia_catedral"]["base_url"]

    # Initialize Supabase loader
    db_loader = SupabaseLoader()
    db_loader_instance = db_loader  # Set global instance for handlers

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

    # Start scraping run
    run_id = await db_loader.start_scraping_run("farmacia_catedral", "medicamentos+suplementos")

    try:
        # Create crawler with anti-detection measures
        crawler = PlaywrightCrawler(
            request_handler=router,
            proxy_configuration=proxy_configuration,
            max_requests_per_crawl=settings.max_requests_per_crawl,
            max_request_retries=2,
            headless=True,
        )

        # Start URLs (category pages)
        start_urls = [
            f"{base_url}/categoria/1/medicamentos?marcas=&categorias=&categorias_top=",
            f"{base_url}/categoria/35/suplemento-vitaminico-y-mineral?marcas=&categorias=&categorias_top=",
        ]

        logger.info(f"Starting Farmacia Catedral scraper")
        logger.info(f"Strategy: Lazy scroll category pages, then scrape all products")

        # Enqueue start URLs as category listings
        await crawler.run([
            Request.from_url(url, label="category_listing") for url in start_urls
        ])

        # Get final count from Crawlee storage
        dataset = await crawler.get_dataset()
        data = await dataset.get_data()

        total_scraped = len(data.items)
        logger.info(f"Scraping completed: {total_scraped} products scraped and saved to Supabase")

        # Complete scraping run
        await db_loader.complete_scraping_run(run_id, total_scraped, 0)

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        await db_loader.complete_scraping_run(run_id, 0, 0, str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
