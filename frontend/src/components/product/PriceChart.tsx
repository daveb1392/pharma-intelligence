"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getPriceHistory } from "@/lib/api";
import { PHARMACIES } from "@/lib/constants";

export function PriceChart({ barcode }: { barcode: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["price-history", barcode],
    queryFn: () => getPriceHistory(barcode, 90),
  });

  if (isLoading) {
    return <Skeleton className="w-full h-64" />;
  }

  if (error || !data || data.history.length === 0) {
    return (
      <Card className="p-6 text-center text-sm text-muted-foreground">
        No hay historial de precios disponible aún.
      </Card>
    );
  }

  // Merge all pharmacy data into a unified timeline
  const allDates = new Set<string>();
  data.history.forEach((ph) =>
    ph.data_points.forEach((dp) => allDates.add(dp.date)),
  );

  const sortedDates = Array.from(allDates).sort();
  const chartData = sortedDates.map((date) => {
    const point: Record<string, string | number | null> = { date };
    data.history.forEach((ph) => {
      const dp = ph.data_points.find((d) => d.date === date);
      point[ph.pharmacy_source] = dp?.price ?? null;
    });
    return point;
  });

  return (
    <Card className="p-4">
      <h3 className="font-semibold mb-4 text-sm">
        Historial de precios (90 días)
      </h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickFormatter={(d) => {
              const [, m, day] = d.split("-");
              return `${day}/${m}`;
            }}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            formatter={(value) =>
              `Gs. ${Math.round(Number(value)).toLocaleString("es-PY")}`
            }
            labelFormatter={(label) => {
              const [y, m, d] = String(label).split("-");
              return `${d}/${m}/${y}`;
            }}
          />
          <Legend
            formatter={(value) =>
              PHARMACIES[value]?.shortName || value
            }
          />
          {data.history.map((ph) => (
            <Line
              key={ph.pharmacy_source}
              type="monotone"
              dataKey={ph.pharmacy_source}
              stroke={PHARMACIES[ph.pharmacy_source]?.color || "#666"}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
