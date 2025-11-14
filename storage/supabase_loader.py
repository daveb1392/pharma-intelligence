"""Supabase loader for scraped pharmaceutical data."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from supabase import create_client, Client
from utils.config import get_settings
from utils.logger import get_logger

logger = get_logger()


class SupabaseLoader:
    """Load scraped data to Supabase database."""

    def __init__(self):
        """Initialize Supabase client."""
        settings = get_settings()
        self.client: Client = create_client(
            settings.supabase_url, settings.supabase_key
        )
        logger.info("Supabase client initialized")

    async def start_scraping_run(
        self, pharmacy_source: str, categories: str
    ) -> str:
        """
        Start a new scraping run and return the run ID.

        Args:
            pharmacy_source: Name of the pharmacy being scraped
            categories: Categories being scraped

        Returns:
            UUID of the scraping run
        """
        run_id = str(uuid.uuid4())

        try:
            data = {
                "id": run_id,
                "pharmacy_source": pharmacy_source,
                "category": categories,
                "status": "running",
                "started_at": datetime.utcnow().isoformat(),
            }

            result = self.client.table("scraping_runs").insert(data).execute()
            logger.info(f"Started scraping run {run_id} for {pharmacy_source}")
            return run_id

        except Exception as e:
            logger.error(f"Error starting scraping run: {e}")
            # Return run_id anyway so scraper can continue
            return run_id

    async def upsert_product(self, product_data: Dict[str, Any]) -> Optional[str]:
        """
        Insert or update a product in Supabase.
        A trigger will automatically track price changes to price_history table.

        Args:
            product_data: Dictionary with product information

        Returns:
            Product ID if successful, None otherwise
        """
        try:
            # Add timestamp
            product_data["scraped_at"] = datetime.utcnow().isoformat()

            # Upsert product (insert or update based on unique constraint)
            result = (
                self.client.table("products")
                .upsert(product_data, on_conflict="pharmacy_source,site_code")
                .execute()
            )

            if result.data:
                product_id = result.data[0].get("id")
                logger.debug(
                    f"Upserted product {product_data.get('product_name')} "
                    f"(ID: {product_id})"
                )
                return product_id
            else:
                logger.warning(f"No data returned for product upsert")
                return None

        except Exception as e:
            logger.error(
                f"Error upserting product {product_data.get('product_name')}: {e}"
            )
            return None

    async def insert_product_urls(self, urls_list: list[Dict[str, Any]]) -> int:
        """
        Insert product URLs to product_urls table for Phase 1.

        Args:
            urls_list: List of dicts with keys: pharmacy_source, product_url, site_code

        Returns:
            Number of URLs inserted (excluding duplicates)
        """
        try:
            if not urls_list:
                logger.warning("No URLs to insert")
                return 0

            # Add timestamp to all records
            for url_data in urls_list:
                url_data["created_at"] = datetime.utcnow().isoformat()

            # Batch insert with upsert (on conflict: pharmacy_source, product_url)
            result = (
                self.client.table("product_urls")
                .upsert(urls_list, on_conflict="pharmacy_source,product_url")
                .execute()
            )

            inserted = len(result.data) if result.data else 0
            logger.info(f"Inserted {inserted} product URLs")
            return inserted

        except Exception as e:
            logger.error(f"Error inserting product URLs: {e}")
            return 0

    async def insert_barcode_snapshot(self, product_data: Dict[str, Any]) -> Optional[str]:
        """
        Insert a daily snapshot for barcode tracking campaign.
        Captures price data even if unchanged (unlike price_history).

        Args:
            product_data: Dictionary with product information

        Returns:
            Snapshot ID if successful, None otherwise
        """
        try:
            snapshot_data = {
                "product_id": product_data.get("id"),  # Product ID from products table
                "pharmacy_source": product_data.get("pharmacy_source"),
                "site_code": product_data.get("site_code"),
                "barcode": product_data.get("barcode"),
                "product_name": product_data.get("product_name"),
                "brand": product_data.get("brand"),
                "product_url": product_data.get("product_url"),
                "current_price": product_data.get("current_price"),
                "original_price": product_data.get("original_price"),
                "discount_percentage": product_data.get("discount_percentage"),
                "discount_amount": product_data.get("discount_amount"),
                "bank_discount_price": product_data.get("bank_discount_price"),
                "bank_discount_bank": product_data.get("bank_discount_bank"),
                "in_stock": product_data.get("in_stock"),
                "requires_prescription": product_data.get("requires_prescription"),
                "scraped_at": product_data.get("scraped_at", datetime.utcnow().isoformat()),
                "snapshot_date": datetime.utcnow().date().isoformat(),
            }

            # Upsert: one snapshot per product per day
            result = (
                self.client.table("barcode_tracking_snapshots")
                .upsert(snapshot_data, on_conflict="pharmacy_source,barcode,snapshot_date")
                .execute()
            )

            if result.data:
                snapshot_id = result.data[0].get("id")
                logger.debug(f"Inserted snapshot for {product_data.get('product_name')}")
                return snapshot_id
            else:
                logger.warning(f"No data returned for snapshot insert")
                return None

        except Exception as e:
            logger.error(f"Error inserting snapshot for {product_data.get('product_name')}: {e}")
            return None

    async def get_urls_to_scrape(self, pharmacy_source: str, category: Optional[str] = None) -> list[str]:
        """
        Get product URLs that need scraping from product_urls table.

        Args:
            pharmacy_source: Pharmacy source to filter by
            category: Optional category to filter by (e.g., "medicamentos", "nutricion-y-deporte")

        Returns:
            List of product URLs to scrape
        """
        try:
            # Query product_urls table for this pharmacy
            query = (
                self.client.table("product_urls")
                .select("product_url")
                .eq("pharmacy_source", pharmacy_source)
            )

            # Add category filter if specified
            if category:
                query = query.eq("category", category)

            result = query.execute()

            urls = [row["product_url"] for row in result.data if row.get("product_url")]
            category_msg = f" (category: {category})" if category else ""
            logger.info(f"Found {len(urls)} URLs to scrape for {pharmacy_source}{category_msg}")
            return urls

        except Exception as e:
            logger.error(f"Error getting URLs to scrape: {e}")
            return []

    async def get_checkpoint(self, pharmacy_source: str, category: str) -> int:
        """
        Get the last checkpoint (page number) for resuming URL collection.

        Args:
            pharmacy_source: Pharmacy source
            category: Category being scraped

        Returns:
            Last page number scraped, or 0 if no checkpoint exists
        """
        try:
            result = (
                self.client.table("scraping_checkpoints")
                .select("page_number")
                .eq("pharmacy_source", pharmacy_source)
                .eq("category", category)
                .execute()
            )

            if result.data and len(result.data) > 0:
                page_num = result.data[0].get("page_number", 0)
                logger.info(f"Resuming from checkpoint: page {page_num}")
                return page_num
            else:
                logger.info("No checkpoint found, starting from page 0")
                return 0

        except Exception as e:
            logger.warning(f"Error getting checkpoint: {e}, starting from page 0")
            return 0

    async def save_checkpoint(self, pharmacy_source: str, category: str, page_number: int) -> None:
        """
        Save checkpoint for resuming URL collection later.

        Args:
            pharmacy_source: Pharmacy source
            category: Category being scraped
            page_number: Current page number
        """
        try:
            data = {
                "pharmacy_source": pharmacy_source,
                "category": category,
                "page_number": page_number,
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Upsert checkpoint
            self.client.table("scraping_checkpoints").upsert(
                data, on_conflict="pharmacy_source,category"
            ).execute()

            logger.debug(f"Checkpoint saved: page {page_number}")

        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")

    async def complete_scraping_run(
        self,
        run_id: str,
        products_scraped: int,
        products_failed: int,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Mark a scraping run as completed.

        Args:
            run_id: UUID of the scraping run
            products_scraped: Number of products successfully scraped
            products_failed: Number of products that failed
            error_message: Optional error message if run failed
        """
        try:
            data = {
                "status": "failed" if error_message else "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "products_scraped": products_scraped,
                "products_failed": products_failed,
            }

            if error_message:
                data["error_message"] = error_message

            result = (
                self.client.table("scraping_runs")
                .update(data)
                .eq("id", run_id)
                .execute()
            )

            logger.info(
                f"Completed scraping run {run_id}: {products_scraped} scraped, "
                f"{products_failed} failed"
            )

        except Exception as e:
            logger.error(f"Error completing scraping run {run_id}: {e}")
