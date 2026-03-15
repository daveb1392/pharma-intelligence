import { BookOpen, Calendar } from "lucide-react";
import Link from "next/link";
import type { Metadata } from "next";

import { Card } from "@/components/ui/card";
import { getAllPosts } from "@/lib/blog";

export const metadata: Metadata = {
  title: "Blog - PrecioFarma",
  description:
    "Reportes, análisis de precios y consejos para ahorrar en medicamentos en Paraguay",
};

export default function BlogPage() {
  const posts = getAllPosts();

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Blog & Insights</h1>
        <p className="text-muted-foreground">
          Análisis de precios, tendencias y consejos para ahorrar en farmacias
          de Paraguay.
        </p>
      </div>

      {posts.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-20 h-20 rounded-full bg-emerald-50 mx-auto mb-4 flex items-center justify-center">
            <BookOpen className="h-10 w-10 text-emerald-300" />
          </div>
          <p className="text-muted-foreground">
            Próximamente publicaremos reportes y análisis.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <Link key={post.slug} href={`/blog/${post.slug}`}>
              <Card className="p-6 hover:shadow-md transition-all duration-200 cursor-pointer">
                <div className="flex items-start gap-1 text-xs text-muted-foreground mb-2">
                  <Calendar className="h-3 w-3 mt-0.5" />
                  <time dateTime={post.date}>
                    {new Date(post.date).toLocaleDateString("es-PY", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </time>
                </div>
                <h2 className="text-lg font-semibold mb-2 group-hover:text-emerald-600">
                  {post.title}
                </h2>
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {post.excerpt}
                </p>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
