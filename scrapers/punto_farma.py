"""Punto Farma scraper for pharmaceutical products."""

import asyncio
import re
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


@router.default_handler
async def handle_product_page(context: PlaywrightCrawlingContext) -> None:
    """Handle product detail pages."""
    logger.info(f"Processing product page: {context.request.url}")

    try:
        # Wait for product name to load
        await context.page.wait_for_selector("h1", timeout=10000)
        await context.page.wait_for_timeout(1000)

        # Get page HTML
        html = await context.page.content()

        # Extract product data
        product_data = PuntoFarmaProduct.extract_from_html(html, context.request.url)

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
    """Handle ONE batch of category listing, then re-enqueue for next batch."""
    url = context.request.url

    # Get batch tracking from user_data
    batch_num = context.request.user_data.get("batch", 1)
    clicks_done = context.request.user_data.get("clicks_done", 0)

    logger.info(f"Processing batch {batch_num} (after {clicks_done} previous clicks): {url}")

    try:
        # Wait for product grid
        await context.page.wait_for_selector("a[href*='/producto/']", timeout=10000)

        base_url = PHARMACY_URLS["punto_farma"]["base_url"]
        batch_size = 20  # Click 20 times per batch (small enough to finish in 30-40 seconds)
        max_total_clicks = 600

        # Click "Cargar más" batch_size times
        clicks_this_batch = 0
        no_button_count = 0

        while clicks_this_batch < batch_size and (clicks_done + clicks_this_batch) < max_total_clicks:
            load_more_button = context.page.locator("button.btn.btn-primary:has-text('Cargar más')").first

            try:
                button_visible = await load_more_button.is_visible()
            except:
                # Page closed or button disappeared
                no_button_count += 1
                if no_button_count >= 2:
                    logger.info(f"Button check failed {no_button_count} times, assuming no more pages")
                    break
                await context.page.wait_for_timeout(1000)
                continue

            if button_visible:
                no_button_count = 0
                await load_more_button.scroll_into_view_if_needed()
                await load_more_button.click()
                clicks_this_batch += 1
                await context.page.wait_for_timeout(200)  # Fast clicking
            else:
                no_button_count += 1
                if no_button_count >= 2:
                    logger.info(f"No more 'Cargar más' button after {clicks_done + clicks_this_batch} total clicks")
                    break
                await context.page.wait_for_timeout(1000)

        total_clicks_now = clicks_done + clicks_this_batch
        logger.info(f"Batch {batch_num}: Clicked {clicks_this_batch} times (total: {total_clicks_now})")

        # Extract and enqueue products
        product_links = await context.page.locator("a[href*='/producto/']").all()
        logger.info(f"Found {len(product_links)} product links on page")

        enqueued = set()
        for link in product_links:
            href = await link.get_attribute("href")
            if href:
                if not href.startswith("http"):
                    href = f"{base_url}{href}" if href.startswith("/") else f"{base_url}/{href}"
                if href not in enqueued:
                    await context.add_requests([Request.from_url(href, label="default")])
                    enqueued.add(href)

        logger.info(f"Batch {batch_num}: Enqueued {len(enqueued)} products")

        # Check if we should continue (button still exists and haven't hit limit)
        if no_button_count < 2 and total_clicks_now < max_total_clicks:
            # Re-enqueue THIS SAME URL with updated batch info
            next_batch = batch_num + 1
            logger.info(f"Enqueueing batch {next_batch} to continue pagination")

            await context.add_requests([
                Request.from_url(
                    url,
                    label="category_listing",
                    user_data={
                        "batch": next_batch,
                        "clicks_done": total_clicks_now
                    }
                )
            ])
        else:
            logger.info(f"Category complete: {total_clicks_now} total pages loaded, {len(enqueued)} products from final batch")

    except Exception as e:
        logger.error(f"Error processing category listing batch {batch_num} at {url}: {e}")


async def main() -> None:
    """Run Punto Farma scraper."""
    global db_loader_instance

    settings = get_settings()
    base_url = PHARMACY_URLS["punto_farma"]["base_url"]

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
    run_id = await db_loader.start_scraping_run("punto_farma", "medicamentos+nutricion")

    try:
        # Create crawler with anti-detection measures
        crawler = PlaywrightCrawler(
            request_handler=router,
            proxy_configuration=proxy_configuration,
            max_requests_per_crawl=settings.max_requests_per_crawl,
            max_request_retries=2,  # Limit retries to avoid getting stuck
            headless=True,
        )

        # Start URLs (category pages)
        start_urls = [
            f"{base_url}/categoria/1/medicamentos",  # 440 pages, 12 products each = ~5,280 products
            f"{base_url}/categoria/238/nutricion-y-deporte",  # 80 pages, ~960 products
        ]

        logger.info(f"Starting Punto Farma scraper with URLs: {start_urls}")

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
