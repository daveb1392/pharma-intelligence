"""Explore Punto Farma website structure."""

import asyncio
from playwright.async_api import async_playwright

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("=" * 60)
        print("PUNTO FARMA EXPLORATION")
        print("=" * 60)

        # Visit homepage
        print("\n1. Visiting homepage...")
        await page.goto("https://www.puntofarma.com.py")
        await page.wait_for_timeout(3000)

        title = await page.title()
        print(f"   Title: {title}")

        # Look for category/product links
        print("\n2. Looking for navigation/categories...")

        # Try common selectors
        nav_links = await page.locator("nav a, .menu a, .category a").all()
        print(f"   Found {len(nav_links)} navigation links")

        if len(nav_links) > 0:
            print("\n   First 10 links:")
            for i, link in enumerate(nav_links[:10]):
                text = await link.text_content()
                href = await link.get_attribute("href")
                print(f"   [{i+1}] {text.strip()} -> {href}")

        # Look for search or category pages
        print("\n3. Checking for product catalog/search...")

        # Try to find products or catalog
        product_links = await page.locator("a[href*='product'], a[href*='producto'], .product a, .item a").all()
        print(f"   Found {len(product_links)} potential product links")

        # Check page source for clues
        print("\n4. Checking page structure...")
        html = await page.content()

        # Look for common e-commerce patterns
        patterns = [
            "medicamentos",
            "productos",
            "catalog",
            "shop",
            "store",
            "farma",
            "product",
        ]

        print("   Keywords found in HTML:")
        for pattern in patterns:
            if pattern in html.lower():
                print(f"   ✓ {pattern}")

        print("\n5. Waiting for user to explore...")
        print("   Browser will stay open for 30 seconds for manual inspection")
        await page.wait_for_timeout(30000)

        await browser.close()

        print("\n" + "=" * 60)
        print("Exploration complete!")
        print("=" * 60)

asyncio.run(explore())
