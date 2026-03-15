"use client";

import { Pill } from "lucide-react";
import { useState } from "react";

interface ProductImageProps {
  src?: string | null;
  alt: string;
  className?: string;
  placeholderClassName?: string;
}

export function ProductImage({
  src,
  alt,
  className = "w-full h-full object-contain",
  placeholderClassName = "h-12 w-12 text-muted-foreground/30",
}: ProductImageProps) {
  const [error, setError] = useState(false);

  if (!src || error) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <Pill className={placeholderClassName} />
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      onError={() => setError(true)}
      loading="lazy"
    />
  );
}
