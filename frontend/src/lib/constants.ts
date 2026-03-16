export const PHARMACIES: Record<
  string,
  {
    displayName: string;
    shortName: string;
    color: string;
    website: string;
  }
> = {
  farma_oliva: {
    displayName: "Farma Oliva",
    shortName: "Oliva",
    color: "#2E7D32",
    website: "https://www.farmaoliva.com.py",
  },
  punto_farma: {
    displayName: "Punto Farma",
    shortName: "Punto",
    color: "#1565C0",
    website: "https://www.puntofarma.com.py",
  },
  farma_center: {
    displayName: "Farma Center",
    shortName: "Center",
    color: "#E65100",
    website: "https://www.farmacenter.com.py",
  },
  farmacia_catedral: {
    displayName: "Farmacia Catedral",
    shortName: "Catedral",
    color: "#6A1B9A",
    website: "https://www.farmaciacatedral.com.py",
  },
};

// Farma Center stored their logo as image_url for all products — treat as no image
const LOGO_URLS = new Set([
  "https://f.fcdn.app/assets/commerce/www.farmacenter.com.py/c305_93b5/public/web/img/logo.svg",
]);

export function getProductImage(imageUrl?: string | null): string | null {
  if (!imageUrl) return null;
  if (LOGO_URLS.has(imageUrl)) return null;
  return imageUrl;
}

export function getPharmacy(source: string) {
  return (
    PHARMACIES[source] ?? {
      displayName: source,
      shortName: source,
      color: "#666",
      website: "#",
    }
  );
}

export function formatPrice(price: number | undefined | null): string {
  if (price == null) return "—";
  return `Gs. ${Math.round(price).toLocaleString("es-PY")}`;
}

export function formatTimeAgo(dateStr: string | undefined): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  if (hours < 1) return "Hace menos de 1 hora";
  if (hours < 24) return `Hace ${hours}h`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Hace 1 día";
  return `Hace ${days} días`;
}
