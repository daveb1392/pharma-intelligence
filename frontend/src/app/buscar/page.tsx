import type { Metadata } from "next";

import { SearchBar } from "@/components/layout/SearchBar";
import { ProductCard } from "@/components/product/ProductCard";
import { searchProducts } from "@/lib/api";

interface Props {
  searchParams: Promise<{ q?: string; page?: string; pharmacy?: string; category?: string }>;
}

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const q = params.q || "";
  return {
    title: q ? `${q} - Buscar` : "Buscar medicamentos",
    description: `Compará precios de ${q} en farmacias de Paraguay`,
  };
}

export default async function SearchPage({ searchParams }: Props) {
  const params = await searchParams;
  const q = params.q || "";
  const page = parseInt(params.page || "1", 10);

  if (!q) {
    return (
      <div className="container mx-auto px-4 py-12 text-center">
        <h1 className="text-2xl font-bold mb-4">Buscar productos</h1>
        <div className="max-w-xl mx-auto">
          <SearchBar size="large" />
        </div>
      </div>
    );
  }

  let data;
  try {
    data = await searchProducts(q, page, params.pharmacy, params.category);
  } catch {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-xl mx-auto mb-6">
          <SearchBar defaultValue={q} />
        </div>
        <p className="text-center text-muted-foreground">
          Error al buscar. Intentá de nuevo.
        </p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="max-w-xl mx-auto mb-6">
        <SearchBar defaultValue={q} />
      </div>

      <p className="text-sm text-muted-foreground mb-4">
        {data.total} resultado{data.total !== 1 ? "s" : ""} para &ldquo;{q}
        &rdquo;
      </p>

      {data.results.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">
            No se encontraron productos para &ldquo;{q}&rdquo;
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {data.results.map((product, i) => (
            <ProductCard
              key={product.barcode || product.group_key || i}
              product={product}
              variant="grid"
            />
          ))}
        </div>
      )}
    </div>
  );
}
