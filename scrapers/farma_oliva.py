"""Farma Oliva scraper for pharmaceutical products."""

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


class FarmaOlivaProduct:
    """Data class for Farma Oliva product extraction."""

    @staticmethod
    def extract_from_html(html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract product data from Farma Oliva product page HTML.

        Args:
            html: HTML content of product page
            url: Product URL

        Returns:
            Dictionary with product data, or None if extraction fails
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Product name
            product_name_elem = soup.select_one(".single-product-header h1.product_title")
            product_name = product_name_elem.get_text(strip=True) if product_name_elem else None

            if not product_name:
                logger.warning(f"No product name found for {url}")
                return None

            # Site code and barcode
            site_code = None
            barcode = None
            code_elem = soup.select_one("#producto-codigo")
            barcode_elem = soup.select_one("#producto-ean")

            if code_elem:
                site_code = code_elem.get_text(strip=True)
            if barcode_elem:
                barcode = barcode_elem.get_text(strip=True)

            # Category path from breadcrumb
            category_path = []
            main_category = None
            breadcrumb = soup.select(".ecommercepro-breadcrumb a")
            for link in breadcrumb:
                category_text = link.get_text(strip=True)
                if category_text and category_text not in ["Inicio", "Catálogo de productos"]:
                    category_path.append(category_text)

            if category_path:
                main_category = category_path[0]

            # Prescription requirement
            requires_prescription = False
            prescription_type = None
            prescription_badge = soup.select_one(".badge-pill")
            if prescription_badge:
                prescription_text = prescription_badge.get_text(strip=True)
                prescription_type = prescription_text
                requires_prescription = "libre" not in prescription_text.lower()

            # Price (remove currency symbols and parse)
            current_price = None
            original_price = None
            discount_percentage = None
            discount_amount = None

            price_elem = soup.select_one("#producto-precio")
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extract numeric price (e.g., "₲. 59.400 *" -> "59400")
                price_match = re.search(r"[\d.]+", price_text.replace(".", ""))
                if price_match:
                    current_price = float(price_match.group())

            # Original price (if discounted)
            original_price_elem = soup.select_one("#producto-precio-anterior")
            if original_price_elem:
                price_text = original_price_elem.get_text(strip=True)
                price_match = re.search(r"[\d.]+", price_text.replace(".", ""))
                if price_match:
                    original_price = float(price_match.group())

            # Discount percentage (from badge)
            discount_badge = soup.select_one(".discount text")
            if discount_badge:
                discount_text = discount_badge.get_text(strip=True)
                discount_match = re.search(r"(\d+)%", discount_text)
                if discount_match:
                    discount_percentage = float(discount_match.group(1))

            # Calculate discount amount if we have both prices
            if current_price and original_price:
                discount_amount = original_price - current_price
                # Recalculate percentage if not found in badge
                if not discount_percentage:
                    discount_percentage = round((discount_amount / original_price) * 100, 2)

            # Product details (Presentación, Droga, etc.)
            product_details = {}
            short_desc = soup.select_one(".ecommercepro-product-details__short-description")
            if short_desc:
                # Extract key-value pairs
                headers = short_desc.find_all("h6")
                for header in headers:
                    key = header.get_text(strip=True).replace(":", "").strip()
                    value_elem = header.find_next_sibling("p")
                    if value_elem:
                        value = value_elem.get_text(strip=True)
                        product_details[key] = value

            # Product description (from tab)
            product_description = None
            desc_tab = soup.select_one("#tab-1")
            if desc_tab:
                product_description = desc_tab.get_text(separator=" ", strip=True)

            # Image URL
            image_url = None
            image_elem = soup.select_one(".ecommercepro-product-gallery__image img")
            if image_elem:
                image_url = image_elem.get("src") or image_elem.get("data-src")

            # Build product dictionary
            product_data = {
                "site_code": site_code,
                "barcode": barcode,
                "product_name": product_name,
                "brand": product_details.get("Droga"),  # Using "Droga" as brand proxy
                "product_description": product_description,
                "product_details": product_details,
                "category_path": category_path,
                "main_category": main_category,
                "current_price": current_price,
                "original_price": original_price,
                "discount_percentage": discount_percentage,
                "discount_amount": discount_amount,
                "bank_discount_price": None,  # Not present on this page
                "bank_discount_bank_name": None,
                "bank_payment_offers": None,
                "requires_prescription": requires_prescription,
                "prescription_type": prescription_type,
                "payment_methods": None,  # Not on product page
                "shipping_options": None,  # Not on product page
                "image_url": image_url,
                "image_urls": [image_url] if image_url else [],
                "pharmacy_source": "farma_oliva",
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
        # Wait for price element to be populated by JavaScript
        await context.page.wait_for_selector("#producto-precio", timeout=5000)

        # Wait a bit more for any discount JavaScript to execute
        await context.page.wait_for_timeout(1000)

        # Get page HTML after JavaScript execution
        html = await context.page.content()

        # Extract product data
        product_data = FarmaOlivaProduct.extract_from_html(html, context.request.url)

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
    """Handle category listing pages to discover product links."""
    logger.info(f"Processing category listing: {context.request.url}")

    try:
        # Wait for product grid to load
        await context.page.wait_for_selector(".products", timeout=10000)

        # Extract all product links
        product_links = await context.page.locator(".product a.ecommercepro-LoopProduct-link").all()

        logger.info(f"Found {len(product_links)} products on page")

        # Enqueue each product link
        for link in product_links:
            href = await link.get_attribute("href")
            if href:
                # Convert relative URLs to absolute
                if not href.startswith("http"):
                    base_url = PHARMACY_URLS["farma_oliva"]["base_url"]
                    href = f"{base_url}/{href.lstrip('/')}"

                await context.add_requests([Request.from_url(href, label="default")])
                logger.debug(f"Enqueued product: {href}")

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
    """Run Farma Oliva scraper."""
    global db_loader_instance

    settings = get_settings()
    base_url = PHARMACY_URLS["farma_oliva"]["base_url"]

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
    run_id = await db_loader.start_scraping_run("farma_oliva", "medicamentos+suplementos")

    try:
        # Create crawler with anti-detection measures
        # Fingerprint generation is enabled by default to avoid bot detection
        crawler = PlaywrightCrawler(
            request_handler=router,
            proxy_configuration=proxy_configuration,
            max_requests_per_crawl=settings.max_requests_per_crawl,
            max_request_retries=2,  # Limit retries to avoid getting stuck
            headless=True,
        )

        # Start URLs (category pages)
        start_urls = [
            f"{base_url}/catalogo/medicamentos-c3",  # 3896 products
            f"{base_url}/catalogo/suplementos-nutricionales-c5",  # 575 products
        ]

        logger.info(f"Starting Farma Oliva scraper with URLs: {start_urls}")

        # Enqueue start URLs as category listings
        await crawler.run([
            Request.from_url(url, label="category_listing") for url in start_urls
        ])

        # Get final count from Crawlee storage (products already saved to Supabase during scraping)
        dataset = await crawler.get_dataset()
        data = await dataset.get_data()

        total_scraped = len(data.items)
        logger.info(f"Scraping completed: {total_scraped} products scraped and saved to Supabase")

        # Complete scraping run (products were already saved during crawling)
        await db_loader.complete_scraping_run(run_id, total_scraped, 0)

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        await db_loader.complete_scraping_run(run_id, 0, 0, str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
