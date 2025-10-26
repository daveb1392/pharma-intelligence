"""Test parsing Punto Farma POST API response."""

import re
import json


def parse_nextjs_response(response_text: str) -> dict:
    """Parse Next.js Server Component response to extract JSON data.

    The response format is:
    0:["$@1",["g1e-1giqLuQXaoHVgcmF4",null]]
    2:T636,Product description text...
    1:{"ok":true,"results":[...]}

    We need to extract line starting with `1:{...}`
    """
    # Find the JSON object that starts with "1:{"
    match = re.search(r'1:(\{"ok".*\})', response_text)
    if match:
        json_str = match.group(1)
        data = json.loads(json_str)
        return data
    return None


# Read saved response
with open("punto_farma_page_1_response.txt", "r") as f:
    response_text = f.read()

# Parse
data = parse_nextjs_response(response_text)

if data:
    print(f"✓ Successfully parsed response!")
    print(f"  ok: {data.get('ok')}")
    print(f"  total products: {data.get('total')}")
    print(f"  results count: {len(data.get('results', []))}")
    print()

    # Show first 3 products
    results = data.get("results", [])
    for i, product in enumerate(results[:3], 1):
        print(f"Product {i}:")
        print(f"  codigo (site_code): {product.get('codigo')}")
        print(f"  codigoBarra (barcode): {product.get('codigoBarra')}")
        print(f"  descripcion: {product.get('descripcion')}")
        print(f"  precio: {product.get('precio')}")
        print(f"  descuento: {product.get('descuento')}%")
        print()

    # Build URLs
    print("Product URLs:")
    for i, product in enumerate(results[:5], 1):
        codigo = product.get('codigo')
        descripcion = product.get('descripcion', '')
        # Convert to URL slug
        slug = descripcion.lower().replace(' ', '-').replace('--', '-')
        # Remove special chars
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        url = f"https://www.puntofarma.com.py/producto/{codigo}/{slug}"
        print(f"  {url}")
else:
    print("✗ Failed to parse response")
