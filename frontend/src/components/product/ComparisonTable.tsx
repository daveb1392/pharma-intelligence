"use client";

import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatPrice, formatTimeAgo, getPharmacy } from "@/lib/constants";
import type { PharmacyPrice } from "@/types/product";

export function ComparisonTable({
  pharmacies,
  bestPrice,
}: {
  pharmacies: PharmacyPrice[];
  bestPrice?: number;
}) {
  return (
    <div className="space-y-3">
      {pharmacies.map((p) => {
        const pharmacy = getPharmacy(p.pharmacy_source);
        const isBest =
          bestPrice != null && p.current_price === bestPrice;

        return (
          <Card
            key={p.pharmacy_source}
            className={`p-4 ${isBest ? "border-emerald-500 bg-emerald-50/50" : ""}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: pharmacy.color }}
                  />
                  <span className="font-medium text-sm">
                    {pharmacy.displayName}
                  </span>
                  {isBest && (
                    <Badge className="bg-emerald-600 text-xs">
                      Mejor precio
                    </Badge>
                  )}
                </div>

                {/* Prices */}
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="text-xl font-bold">
                    {formatPrice(p.current_price)}
                  </span>
                  {p.original_price &&
                    p.original_price !== p.current_price && (
                      <span className="text-sm text-muted-foreground line-through">
                        {formatPrice(p.original_price)}
                      </span>
                    )}
                  {p.discount_percentage != null &&
                    p.discount_percentage > 0 && (
                      <Badge variant="destructive" className="text-xs">
                        -{Math.round(p.discount_percentage)}%
                      </Badge>
                    )}
                </div>

                {/* Bank discount */}
                {p.bank_discount_price != null && (
                  <div className="mt-2 p-2 rounded-lg bg-blue-50 border border-blue-200">
                    <p className="text-sm font-medium text-blue-800">
                      Con {p.bank_discount_bank_name || "tarjeta"}:{" "}
                      <span className="font-bold">
                        {formatPrice(p.bank_discount_price)}
                      </span>
                    </p>
                    {p.bank_payment_offers && (
                      <p className="text-xs text-blue-600 mt-0.5">
                        {p.bank_payment_offers}
                      </p>
                    )}
                  </div>
                )}

                <p className="text-xs text-muted-foreground mt-2">
                  {formatTimeAgo(p.scraped_at)}
                </p>
              </div>

              {/* Link to pharmacy */}
              {p.product_url && (
                <a
                  href={p.product_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 p-2 rounded-lg hover:bg-muted transition-colors"
                  title={`Ver en ${pharmacy.displayName}`}
                >
                  <ExternalLink className="h-4 w-4 text-muted-foreground" />
                </a>
              )}
            </div>
          </Card>
        );
      })}
    </div>
  );
}
