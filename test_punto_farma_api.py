"""Test Punto Farma pagination API using POST request."""

import asyncio
import httpx
import json


async def test_punto_farma_api():
    """Test POST request to Punto Farma pagination endpoint."""

    url = "https://www.puntofarma.com.py/categoria/1/medicamentos"

    # Headers from browser request
    headers = {
        "accept": "text/x-component",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "text/plain;charset=UTF-8",
        "next-action": "48e9f2eca478537e00a58539a9f9edcf2e1dff77",
        "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22categoria%22%2C%7B%22children%22%3A%5B%221%22%2C%7B%22children%22%3A%5B%22medicamentos%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%5D%7D%5D%7D%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
        "origin": "https://www.puntofarma.com.py",
        "referer": "https://www.puntofarma.com.py/categoria/1/medicamentos",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test pages 1-3
        for page in range(1, 4):
            payload = f'["/productos/categoria/1?p={page}&orderBy=destacado&descuento="]'

            print(f"\n{'='*80}")
            print(f"Testing page {page}")
            print(f"Payload: {payload}")
            print(f"{'='*80}")

            try:
                response = await client.post(url, headers=headers, content=payload)

                print(f"Status: {response.status_code}")
                print(f"Content-Type: {response.headers.get('content-type')}")
                print(f"Response length: {len(response.text)} characters")

                # Save full response to file for analysis
                if page == 1:
                    with open(f"punto_farma_page_{page}_response.txt", "w") as f:
                        f.write(response.text)
                    print(f"\nSaved full response to punto_farma_page_{page}_response.txt")

                # Try to find product URLs in response
                if "/producto/" in response.text:
                    import re
                    # Pattern: /producto/139212/novalgina-adulto-1-g-x-10-comprimidos
                    product_urls = re.findall(r'/producto/(\d+)/([^"\'\\]+)', response.text)
                    unique_urls = list(dict.fromkeys(product_urls))  # Remove duplicates preserving order
                    print(f"\nFound {len(unique_urls)} unique product URLs:")
                    for code, slug in unique_urls[:10]:  # Show first 10
                        print(f"  - /producto/{code}/{slug}")
                else:
                    print("\nNo /producto/ URLs found in response")
                    print(f"Response sample: {response.text[:200]}")

            except Exception as e:
                print(f"Error: {e}")

            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(test_punto_farma_api())
