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
