"""Simple pagination test without Crawlee queue."""

import asyncio
from playwright.async_api import async_playwright

async def test_pagination():
    """Test if we can discover all pages."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        base_url = "https://www.farmaoliva.com.py"
        current_url = f"{base_url}/catalogo/medicamentos-c3"

        pages_discovered = []
        max_pages = 30  # Test first 30 pages

        for i in range(max_pages):
            print(f"\nPage {i+1}: {current_url}")
            pages_discovered.append(current_url)

            try:
                await page.goto(current_url, timeout=30000)
                await page.wait_for_selector(".products", timeout=10000)

                # Count products
                products = await page.locator(".product").count()
                print(f"  Products on page: {products}")

                # Check for next button
                next_button = page.locator("a.next.page-numbers").first
                next_count = await next_button.count()
                print(f"  Next button count: {next_count}")

                if next_count > 0:
                    next_href = await next_button.get_attribute("href")
                    print(f"  Next href (raw): {next_href}")

                    if next_href:
                        # Convert to absolute URL
                        if not next_href.startswith("http"):
                            current_url = f"{base_url}/{next_href.lstrip('/')}"
                        else:
                            current_url = next_href
                        print(f"  Next URL (absolute): {current_url}")
                    else:
                        print("  No href found - stopping")
                        break
                else:
                    print("  No next button - last page reached")
                    break

            except Exception as e:
                print(f"  ERROR: {e}")
                break

        await browser.close()

        print(f"\n{'='*60}")
        print(f"RESULTS:")
        print(f"{'='*60}")
        print(f"Total pages discovered: {len(pages_discovered)}")
        print(f"\nAll discovered URLs:")
        for url in pages_discovered:
            print(f"  {url}")

asyncio.run(test_pagination())
