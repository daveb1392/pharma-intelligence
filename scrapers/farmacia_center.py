"""Farmacia Center scraper for pharmaceutical products."""

import asyncio
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

            # Product name (h1.tit)
            product_name_elem = soup.select_one("h1.tit")
            product_name = product_name_elem.get_text(strip=True) if product_name_elem else None

            if not product_name:
                logger.warning(f"No product name found for {url}")
                return None

            # Site code and barcode from .cod div: "10030348-7703281002468"
            site_code = None
            barcode = None
            cod_div = soup.select_one(".cod")
            if cod_div:
                cod_text = cod_div.get_text(strip=True)
                # Split on hyphen: first part is site_code, second is barcode
                parts = cod_text.split("-")
                if len(parts) == 2:
                    site_code = parts[0].strip()
                    barcode = parts[1].strip()
                elif len(parts) == 1:
                    # Only site code, no barcode
                    site_code = parts[0].strip()

            # Brand from data-tit attribute: "Medicamentos ABBOTT "
            brand = None
            central_div = soup.select_one("#central[data-tit]")
            if central_div:
                data_tit = central_div.get("data-tit", "")
                # Extract brand from "Medicamentos ABBOTT " or similar
                match = re.search(r"(?:Medicamentos|Suplementos)\s+(.+)", data_tit, re.IGNORECASE)
                if match:
                    brand = match.group(1).strip()

            # Category from data-tit (first word: Medicamentos or Suplementos)
            main_category = None
            if central_div:
                data_tit = central_div.get("data-tit", "")
                if data_tit:
                    # First word is the category
                    category_match = re.match(r"^(\w+)", data_tit)
                    if category_match:
                        main_category = category_match.group(1)

            # Small description (optional): <div class="desc"><p>...</p></div>
            small_description = None
            desc_div = soup.select_one(".desc p")
            if desc_div:
                small_description = desc_div.get_text(strip=True)

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
                "product_description": small_description,
                "product_details": {},
                "category_path": [main_category] if main_category else [],
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
                "pharmacy_source": "farmacia_center",
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
        await context.page.wait_for_selector("h1.tit", timeout=10000)
        await context.page.wait_for_timeout(1000)

        # Get page HTML
        html = await context.page.content()

        # Extract product data
        product_data = FarmaciaCenterProduct.extract_from_html(html, context.request.url)

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

            # Click "Siguiente" button to go to next product
            # <button title="Producto siguiente" class="btnSiguiente btnNav">
            next_button = context.page.locator("button.btnSiguiente.btnNav").first
            button_count = await next_button.count()

            if button_count > 0:
                # Get current product number
                current_num_elem = context.page.locator(".nav .info .actual").first
                total_num_elem = context.page.locator(".nav .info .tot").first

                current_num = await current_num_elem.text_content() if await current_num_elem.count() > 0 else "?"
                total_num = await total_num_elem.text_content() if await total_num_elem.count() > 0 else "?"

                logger.info(f"Product {current_num}/{total_num} - clicking next...")

                # Click next button
                await next_button.click()
                await context.page.wait_for_timeout(1500)  # Wait for navigation

                # Get new URL and enqueue it
                new_url = context.page.url
                if new_url != context.request.url:
                    await context.add_requests([Request.from_url(new_url, label="default")])
                    logger.debug(f"Enqueued next product: {new_url}")
                else:
                    logger.info("Reached last product (URL didn't change)")
            else:
                logger.info("No next button found - this might be the last product")

        else:
            logger.warning(f"Failed to extract product from {context.request.url}")

    except Exception as e:
        logger.error(f"Error processing product page {context.request.url}: {e}")


async def main() -> None:
    """Run Farmacia Center scraper."""
    global db_loader_instance

    settings = get_settings()
    base_url = PHARMACY_URLS["farmacia_center"]["base_url"]

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
    run_id = await db_loader.start_scraping_run("farmacia_center", "medicamentos")

    try:
        # Create crawler with anti-detection measures
        crawler = PlaywrightCrawler(
            request_handler=router,
            proxy_configuration=proxy_configuration,
            max_requests_per_crawl=settings.max_requests_per_crawl,
            max_request_retries=2,
            headless=True,
        )

        # Start with first product in medicamentos category
        # The scraper will automatically navigate through all 3,443 products using the "next" button
        start_urls = [
            f"{base_url}/medicamentos",  # Category page - we'll navigate to first product
        ]

        logger.info(f"Starting Farmacia Center scraper")
        logger.info(f"Strategy: Navigate through products using 'Siguiente' button")
        logger.info(f"Expected products: 3,443")

        # Run crawler - start from the medicamentos category page
        await crawler.run(start_urls)

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
