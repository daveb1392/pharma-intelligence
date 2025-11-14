"""
Quick check of what's in barcode_tracking_snapshots table.
"""

from storage.supabase_loader import SupabaseLoader

loader = SupabaseLoader()

# Count snapshots
result = loader.client.table("barcode_tracking_snapshots").select("id", count="exact").execute()
print(f"Total snapshots in DB: {result.count}")

# Count by pharmacy
result = loader.client.table("barcode_tracking_snapshots").select("pharmacy_source", count="exact").execute()
by_pharmacy = {}
for record in result.data:
    pharmacy = record["pharmacy_source"]
    by_pharmacy[pharmacy] = by_pharmacy.get(pharmacy, 0) + 1

print("\nBy pharmacy:")
for pharmacy, count in sorted(by_pharmacy.items()):
    print(f"  {pharmacy}: {count}")

# Count by date
result = loader.client.table("barcode_tracking_snapshots").select("snapshot_date", count="exact").execute()
by_date = {}
for record in result.data:
    date = record["snapshot_date"]
    by_date[date] = by_date.get(date, 0) + 1

print("\nBy date:")
for date in sorted(by_date.keys(), reverse=True):
    print(f"  {date}: {by_date[date]}")

# Show tracking URLs count
result = loader.client.table("barcode_tracking_urls").select("id", count="exact").execute()
print(f"\nTracking URLs: {result.count}")
