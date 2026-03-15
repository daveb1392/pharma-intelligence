import type { Metadata } from "next";
import Link from "next/link";

import { ComparisonTable } from "@/components/product/ComparisonTable";
import { PriceChart } from "@/components/product/PriceChart";
import { Badge } from "@/components/ui/badge";
import { getComparison } from "@/lib/api";
import { formatPrice } from "@/lib/constants";

interface Props {
  params: Promise<{ barcode: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { barcode } = await params;
  try {
    const data = await getComparison(barcode);
    return {
      title: `${data.product_name || barcode} - Comparar precios`,
      description: `Compará precios de ${data.product_name} en ${data.pharmacies.length} farmacias de Paraguay. Mejor precio: ${formatPrice(data.best_price)}`,
    };
  } catch {
    return { title: "Producto no encontrado" };
  }
}

export default async function ProductPage({ params }: Props) {
  const { barcode } = await params;

  let data;
  try {
    data = await getComparison(barcode);
  } catch {
    return (
      <div className="container mx-auto px-4 py-12 text-center">
        <h1 className="text-xl font-bold mb-2">Producto no encontrado</h1>
        <p className="text-muted-foreground mb-4">
          No se encontró un producto con código {barcode}
        </p>
        <Link href="/" className="text-emerald-600 hover:underline">
          Volver al inicio
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-3xl">
      {/* Product header */}
      <div className="flex gap-4 mb-6">
        {data.image_url && (
          <img
            src={data.image_url}
            alt={data.product_name || ""}
            className="w-20 h-20 md:w-28 md:h-28 object-contain rounded-lg border shrink-0"
          />
        )}
        <div>
          <h1 className="text-xl md:text-2xl font-bold leading-tight">
            {data.product_name}
          </h1>
          {data.brand && (
            <p className="text-muted-foreground mt-1">{data.brand}</p>
          )}
          {data.main_category && (
            <Badge variant="secondary" className="mt-2">
              {data.main_category}
            </Badge>
          )}
          <p className="text-xs text-muted-foreground mt-1">
            Código: {barcode}
          </p>
        </div>
      </div>

      {/* Savings highlight */}
      {data.savings != null && data.savings > 0 && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4 mb-6 text-center">
          <p className="text-sm text-emerald-800">
            Ahorrás hasta{" "}
            <span className="font-bold text-lg">
              {formatPrice(data.savings)}
            </span>{" "}
            comparando farmacias
          </p>
        </div>
      )}

      {/* Comparison table */}
      <h2 className="font-semibold text-lg mb-3">
        Precios en {data.pharmacies.length} farmacia
        {data.pharmacies.length !== 1 ? "s" : ""}
      </h2>
      <ComparisonTable
        pharmacies={data.pharmacies}
        bestPrice={data.best_price ?? undefined}
      />

      {/* Price history chart */}
      <div className="mt-8">
        <PriceChart barcode={barcode} />
      </div>
    </div>
  );
}
