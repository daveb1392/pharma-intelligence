import { Pill } from "lucide-react";
import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t bg-muted/50 hidden md:block">
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-4 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Pill className="h-5 w-5 text-emerald-600" />
              <span className="font-bold">PrecioFarma</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Compará precios de medicamentos en farmacias de Paraguay y ahorrá.
            </p>
          </div>
          <div>
            <h3 className="font-semibold mb-3 text-sm">Farmacias</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>Farma Oliva</li>
              <li>Punto Farma</li>
              <li>Farma Center</li>
              <li>Farmacia Catedral</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-3 text-sm">Explorar</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link href="/categorias" className="hover:text-foreground">
                  Categorías
                </Link>
              </li>
              <li>
                <Link href="/blog" className="hover:text-foreground">
                  Blog & Insights
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-3 text-sm">Mi Cuenta</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link
                  href="/cuenta/favoritos"
                  className="hover:text-foreground"
                >
                  Mis Favoritos
                </Link>
              </li>
              <li>
                <Link href="/cuenta/alertas" className="hover:text-foreground">
                  Mis Alertas
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-4 border-t text-center text-xs text-muted-foreground">
          PrecioFarma &copy; {new Date().getFullYear()} &mdash; Los precios son
          referenciales y pueden variar.
        </div>
      </div>
    </footer>
  );
}
