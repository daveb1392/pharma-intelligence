"""
Step 2: Daily scraper for marked barcode URLs.
Scrapes only URLs marked with track_daily=true in product_urls table.
Designed for GitHub Actions daily runs.
"""

import asyncio
from datetime import datetime, timedelta
from crawlee import ConcurrencySettings
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from bs4 import BeautifulSoup
import json
from storage.supabase_loader import SupabaseLoader
from utils.logger import get_logger

logger = get_logger()


async def get_daily_tracking_urls(loader: SupabaseLoader) -> dict:
    """
    Get URLs from barcode_tracking_urls table.

    Returns:
        Dict with pharmacy_source as keys, list of URLs as values
    """
    logger.info("Fetching URLs from barcode_tracking_urls table...")

    try:
        # Query barcode_tracking_urls table
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
# FARMA OLIVA HANDLER
# ============================================================================

async def scrape_farma_oliva(context: PlaywrightCrawlingContext, loader: SupabaseLoader, product_info: dict):
    """Scrape Farma Oliva product page."""
    page = context.page
    url = context.request.url

    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        # Product name
        product_name = soup.select_one(".single-product-header h1.product_title")
        product_name = product_name.get_text(strip=True) if product_name else None

        # Site code
        site_code = soup.select_one("#producto-codigo")
        site_code = site_code.get_text(strip=True) if site_code else product_info.get("site_code")

        # Barcode
        barcode = soup.select_one("#producto-ean")
        barcode = barcode.get_text(strip=True) if barcode else product_info.get("barcode")

        # Price
        price_elem = soup.select_one("#producto-precio")
        current_price = None
        if price_elem:
            price_text = price_elem.get_text(strip=True).replace("₲", "").replace(".", "").strip()
            try:
                current_price = float(price_text)
            except:
                pass

        # Original price
        original_price_elem = soup.select_one("#producto-precio-anterior")
        original_price = None
        if original_price_elem:
            price_text = original_price_elem.get_text(strip=True).replace("₲", "").replace(".", "").strip()
            try:
                original_price = float(price_text)
            except:
                pass

        # Brand
        brand = None
        breadcrumbs = soup.select("a.breadcrumb-item")
        for crumb in breadcrumbs:
            text = crumb.get_text(strip=True)
            if "Marca" in text:
                brand = text.replace("Marca", "").strip()
                break

        product_data = {
            "pharmacy_source": "farma_oliva",
            "site_code": site_code,
            "barcode": barcode,
            "product_name": product_name,
            "brand": brand,
            "product_url": url,
            "current_price": current_price,
            "original_price": original_price,
        }

        product_id = await loader.upsert_product(product_data)

        # Insert daily snapshot for tracking campaign
        if product_id:
            product_data["id"] = product_id
            await loader.insert_barcode_snapshot(product_data)

        logger.info(f"✓ {product_name} - ₲{current_price:,.0f}" if current_price else f"✓ {product_name}")

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")


# ============================================================================
# PUNTO FARMA HANDLER
# ============================================================================

async def scrape_punto_farma(context: PlaywrightCrawlingContext, loader: SupabaseLoader, product_info: dict):
    """Scrape Punto Farma product page."""
    page = context.page
    url = context.request.url

    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        # Product name
        product_name = soup.select_one("h1.titulo_titulo__7i65o")
        product_name = product_name.get_text(strip=True) if product_name else None

        # Site code and barcode
        site_code = product_info.get("site_code")
        barcode = product_info.get("barcode")

        # Price
        price_elem = soup.select_one("div.precio_precio__l5AYL")
        current_price = None
        if price_elem:
            price_text = price_elem.get_text(strip=True).replace("₲", "").replace(".", "").strip()
            try:
                current_price = float(price_text)
            except:
                pass

        # Original price
        original_price_elem = soup.select_one("div.precio_precioTachado__2R9jn")
        original_price = None
        if original_price_elem:
            price_text = original_price_elem.get_text(strip=True).replace("₲", "").replace(".", "").strip()
            try:
                original_price = float(price_text)
            except:
                pass

        # Brand
        brand = None
        brand_link = soup.select_one("a.category[href*='/marca/']")
        if brand_link:
            brand = brand_link.get_text(strip=True)

        product_data = {
            "pharmacy_source": "punto_farma",
            "site_code": site_code,
            "barcode": barcode,
            "product_name": product_name,
            "brand": brand,
            "product_url": url,
            "current_price": current_price,
            "original_price": original_price,
        }

        product_id = await loader.upsert_product(product_data)

        # Insert daily snapshot for tracking campaign
        if product_id:
            product_data["id"] = product_id
            await loader.insert_barcode_snapshot(product_data)

        logger.info(f"✓ {product_name} - ₲{current_price:,.0f}" if current_price else f"✓ {product_name}")

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")


# ============================================================================
# FARMACIA CENTER HANDLER
# ============================================================================

async def scrape_farmacia_center(context: PlaywrightCrawlingContext, loader: SupabaseLoader, product_info: dict):
    """Scrape Farmacia Center product page."""
    page = context.page
    url = context.request.url

    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        # Product name
        product_name = soup.select_one("div.tit h1")
        product_name = product_name.get_text(strip=True) if product_name else None

        # Site code and barcode
        codigo_text = soup.select_one("div.cod_bar")
        site_code = product_info.get("site_code")
        barcode = product_info.get("barcode")

        if codigo_text:
            codigo = codigo_text.get_text(strip=True)
            if "-" in codigo:
                parts = codigo.split("-")
                site_code = parts[0]
                barcode = parts[1] if len(parts) > 1 else None

        # Brand
        brand = None
        brand_elem = soup.select_one("[data-tit]")
        if brand_elem:
            tit = brand_elem.get("data-tit", "")
            if "Medicamentos" in tit or "MEDICAMENTOS" in tit:
                brand = tit.split()[-1]

        # Price
        precio_venta = soup.select_one("span.precio_venta")
        current_price = None
        if precio_venta:
            price_text = precio_venta.get_text(strip=True).replace("₲", "").replace(".", "").strip()
            try:
                current_price = float(price_text)
            except:
                pass

        # Original price
        precio_lista = soup.select_one("span.precio_lista")
        original_price = None
        if precio_lista:
            price_text = precio_lista.get_text(strip=True).replace("₲", "").replace(".", "").strip()
            try:
                original_price = float(price_text)
            except:
                pass

        product_data = {
            "pharmacy_source": "farmacia_center",
            "site_code": site_code,
            "barcode": barcode,
            "product_name": product_name,
            "brand": brand,
            "product_url": url,
            "current_price": current_price,
            "original_price": original_price,
        }

        product_id = await loader.upsert_product(product_data)

        # Insert daily snapshot for tracking campaign
        if product_id:
            product_data["id"] = product_id
            await loader.insert_barcode_snapshot(product_data)

        logger.info(f"✓ {product_name} - ₲{current_price:,.0f}" if current_price else f"✓ {product_name}")

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")


# ============================================================================
# FARMACIA CATEDRAL HANDLER
# ============================================================================

async def scrape_farmacia_catedral(context: PlaywrightCrawlingContext, loader: SupabaseLoader, product_info: dict):
    """Scrape Farmacia Catedral product page."""
    page = context.page
    url = context.request.url

    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        # Try JSON-LD first
        json_ld = soup.select_one('script[type="application/ld+json"]')
        product_data = {
            "pharmacy_source": "farmacia_catedral",
            "site_code": product_info.get("site_code"),
            "barcode": product_info.get("barcode"),
            "product_url": url,
        }

        if json_ld:
            try:
                data = json.loads(json_ld.string)
                product_data["product_name"] = data.get("name")
                product_data["barcode"] = data.get("gtin13") or product_info.get("barcode")
                product_data["site_code"] = data.get("sku") or product_info.get("site_code")
                product_data["brand"] = data.get("brand", {}).get("name")

                # Price
                offers = data.get("offers", {})
                price = offers.get("price")
                if price:
                    try:
                        product_data["current_price"] = float(price)
                    except:
                        pass
            except:
                pass

        # HTML fallback
        if not product_data.get("product_name"):
            name_elem = soup.select_one("h1.product-title")
            product_data["product_name"] = name_elem.get_text(strip=True) if name_elem else None

        if not product_data.get("current_price"):
            price_elem = soup.select_one("span.price-final")
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace("₲", "").replace(".", "").strip()
                try:
                    product_data["current_price"] = float(price_text)
                except:
                    pass

        product_id = await loader.upsert_product(product_data)

        # Insert daily snapshot for tracking campaign
        if product_id:
            product_data["id"] = product_id
            await loader.insert_barcode_snapshot(product_data)

        name = product_data.get("product_name")
        price = product_data.get("current_price")
        logger.info(f"✓ {name} - ₲{price:,.0f}" if price else f"✓ {name}")

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")


# ============================================================================
# MAIN SCRAPER
# ============================================================================

async def scrape_pharmacy(pharmacy: str, urls_list: list, loader: SupabaseLoader):
    """Scrape products for a specific pharmacy."""
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
        "farmacia_center": scrape_farmacia_center,
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

    # Configure crawler - use only 1 browser for GitHub Actions stability
    concurrency_settings = ConcurrencySettings(
        max_concurrency=1,  # Single browser for GitHub Actions (prevents crashes)
        min_concurrency=1,
        desired_concurrency=1,
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
    """Main entry point for daily tracker."""
    import os

    start_time = datetime.now()
    logger.info(f"\n{'='*60}")
    logger.info(f"DAILY BARCODE TRACKER - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}\n")

    loader = SupabaseLoader()

    # Get URLs marked for daily tracking
    urls_by_pharmacy = await get_daily_tracking_urls(loader)

    if not urls_by_pharmacy:
        logger.warning("No URLs in barcode_tracking_urls table!")
        logger.info("Run scripts/populate_tracking_urls.py first to populate URLs")
        return

    # Check if filtering by pharmacy (for parallel GitHub Actions jobs)
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
