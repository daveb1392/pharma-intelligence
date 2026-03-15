"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Input } from "@/components/ui/input";

export function SearchBar({
  defaultValue = "",
  size = "default",
}: {
  defaultValue?: string;
  size?: "default" | "large";
}) {
  const [query, setQuery] = useState(defaultValue);
  const router = useRouter();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/buscar?q=${encodeURIComponent(query.trim())}`);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative w-full">
      <Search
        className={`absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground ${
          size === "large" ? "h-5 w-5" : "h-4 w-4"
        }`}
      />
      <Input
        type="search"
        placeholder="Buscar medicamento, marca o código de barras..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className={`${
          size === "large"
            ? "h-14 pl-11 text-lg rounded-xl"
            : "h-10 pl-9 rounded-lg"
        }`}
      />
    </form>
  );
}
