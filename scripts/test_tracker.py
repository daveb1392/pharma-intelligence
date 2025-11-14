"""
Test script to verify daily tracker setup.
"""

import asyncio
from storage.supabase_loader import SupabaseLoader
from utils.logger import get_logger

logger = get_logger()


async def test_setup():
    """Test that daily tracker is properly configured."""
    loader = SupabaseLoader()

    print("\n" + "="*60)
    print("DAILY TRACKER TEST")
    print("="*60 + "\n")

    # Test 1: Check if barcode_tracking_urls table exists
    print("1. Checking database schema...")
    try:
        result = loader.client.table("barcode_tracking_urls").select("*").limit(1).execute()
        print("   ✅ barcode_tracking_urls table exists")
    except Exception as e:
        print(f"   ❌ barcode_tracking_urls table missing: {e}")
        print("   → Run: sql/create_barcode_tracking_table.sql in Supabase")
        return

    # Test 2: Check if any URLs are populated
    print("\n2. Checking tracking URLs...")
    try:
        result = loader.client.table("barcode_tracking_urls").select("*").execute()
        marked_count = len(result.data) if result.data else 0

        if marked_count > 0:
            print(f"   ✅ {marked_count} URLs in tracking table")

            # Breakdown by pharmacy
            by_pharmacy = {}
            for record in result.data:
                pharmacy = record.get("pharmacy_source")
                by_pharmacy[pharmacy] = by_pharmacy.get(pharmacy, 0) + 1

            print("\n   Breakdown by pharmacy:")
            for pharmacy, count in sorted(by_pharmacy.items()):
                print(f"     - {pharmacy}: {count} URLs")
        else:
            print(f"   ⚠️  No URLs in tracking table yet")
            print("   → Run: python scripts/populate_tracking_urls.py")

    except Exception as e:
        print(f"   ❌ Error querying URLs: {e}")
        return

    # Test 3: Check products table
    print("\n3. Checking products with target barcodes...")
    try:
        # Sample of target barcodes
        sample_barcodes = ["7841448001463", "7842228000461", "7848000300095"]

        result = loader.client.table("products").select(
            "pharmacy_source, product_name, barcode, current_price"
        ).in_("barcode", sample_barcodes).execute()

        found_count = len(result.data) if result.data else 0

        if found_count > 0:
            print(f"   ✅ Found {found_count} products (sample of 3 barcodes)")
            print("\n   Sample products:")
            for product in result.data[:3]:
                name = product.get("product_name", "Unknown")[:40]
                pharmacy = product.get("pharmacy_source")
                price = product.get("current_price")
                barcode = product.get("barcode")
                print(f"     - {name}... ({pharmacy})")
                print(f"       Barcode: {barcode} | Price: ₲{price:,.0f}" if price else f"       Barcode: {barcode}")
        else:
            print(f"   ⚠️  No products found with sample barcodes")
            print("   → Run full scrapers first to populate database")

    except Exception as e:
        print(f"   ❌ Error querying products: {e}")
        return

    # Test 4: Check price_history table
    print("\n4. Checking price history tracking...")
    try:
        result = loader.client.table("price_history").select("*").limit(5).execute()
        history_count = len(result.data) if result.data else 0

        if history_count > 0:
            print(f"   ✅ Price history working ({history_count} recent changes)")
        else:
            print(f"   ℹ️  No price changes recorded yet (this is normal for first run)")

    except Exception as e:
        print(f"   ⚠️  Could not check price_history: {e}")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if marked_count > 0:
        print("\n✅ Daily tracker is ready!")
        print("\nNext steps:")
        print("  1. Test locally: python -m scrapers.daily_tracker")
        print("  2. Push to GitHub to enable daily runs")
        print("  3. Check GitHub Actions tab after 2 AM UTC")
    else:
        print("\n⚠️  Setup incomplete")
        print("\nNext steps:")
        print("  1. Run: python scripts/populate_tracking_urls.py")
        print("  2. Test: python -m scrapers.daily_tracker")
        print("  3. Push to GitHub")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_setup())
