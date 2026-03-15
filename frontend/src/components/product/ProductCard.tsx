import { Pill } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatPrice } from "@/lib/constants";
import type { SearchResultItem } from "@/types/product";

export function ProductCard({
  product,
  variant = "grid",
}: {
  product: SearchResultItem;
  variant?: "grid" | "list";
}) {
  const href = product.barcode ? `/producto/${product.barcode}` : "#";

  if (variant === "list") {
    return (
      <Link href={href}>
        <Card className="p-3 hover:shadow-md transition-all duration-200 cursor-pointer">
          <div className="flex gap-3">
            <div className="w-20 h-20 shrink-0 bg-gray-50 rounded-lg flex items-center justify-center overflow-hidden">
              {product.image_url ? (
                <img
                  src={product.image_url}
                  alt={product.product_name || ""}
                  className="w-full h-full object-contain p-1"
                />
              ) : (
                <Pill className="h-8 w-8 text-muted-foreground/30" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-sm leading-tight line-clamp-2">
                {product.product_name}
              </h3>
              {product.brand && (
                <p className="text-xs text-muted-foreground mt-0.5 truncate">
                  {product.brand}
                </p>
              )}
              <div className="flex items-center gap-2 mt-2">
                {product.best_price != null && (
                  <span className="text-lg font-bold text-emerald-600">
                    {formatPrice(product.best_price)}
                  </span>
                )}
                {product.pharmacy_count != null &&
                  product.pharmacy_count > 1 && (
                    <Badge variant="secondary" className="text-xs">
                      {product.pharmacy_count} farmacias
                    </Badge>
                  )}
              </div>
              {product.requires_prescription && (
                <Badge variant="outline" className="text-[10px] mt-1">
                  Receta
                </Badge>
              )}
            </div>
          </div>
        </Card>
      </Link>
    );
  }

  // Grid variant
  return (
    <Link href={href}>
      <Card className="group overflow-hidden hover:shadow-lg transition-all duration-200 h-full flex flex-col">
        {/* Image */}
        <div className="relative bg-gray-50 aspect-square flex items-center justify-center p-4">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.product_name || ""}
              className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
            />
          ) : (
            <Pill className="h-12 w-12 text-muted-foreground/30" />
          )}
          {product.pharmacy_count != null && product.pharmacy_count > 1 && (
            <span className="absolute top-2 right-2 bg-emerald-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
              {product.pharmacy_count} farmacias
            </span>
          )}
        </div>

        {/* Info */}
        <div className="p-3 flex flex-col flex-1">
          <h3 className="text-xs font-medium leading-tight line-clamp-2 mb-1">
            {product.product_name}
          </h3>
          {product.brand && (
            <p className="text-[11px] text-muted-foreground mb-2 truncate">
              {product.brand}
            </p>
          )}
          <div className="mt-auto">
            {product.best_price != null && (
              <span className="text-base font-bold text-emerald-600">
                {formatPrice(product.best_price)}
              </span>
            )}
            {product.requires_prescription && (
              <Badge variant="outline" className="text-[10px] ml-2">
                Receta
              </Badge>
            )}
          </div>
        </div>
      </Card>
    </Link>
  );
}
