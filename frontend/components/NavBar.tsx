"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Scale } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Sözleşmeler", match: (path: string) => path === "/" || path.startsWith("/documents") },
  { href: "/chat", label: "Sohbet", match: (path: string) => path.startsWith("/chat") },
  { href: "/compare", label: "Karşılaştır", match: (path: string) => path.startsWith("/compare") },
  { href: "/how-it-works", label: "Nasıl Çalışır", match: (path: string) => path.startsWith("/how-it-works") },
];

export default function NavBar() {
  const pathname = usePathname() ?? "/";

  return (
    <header
      className="sticky top-0 z-10 border-b-2 border-gold"
      style={{
        background: "linear-gradient(135deg, var(--navy-1), var(--navy-deep))",
        boxShadow: "var(--shadow-nav)",
      }}
    >
      <div className="flex items-center justify-between gap-6 px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5">
          <Scale className="h-5 w-5 text-gold" strokeWidth={1.5} aria-hidden />
          <span className="flex items-baseline gap-2">
            <span className="text-lg font-semibold tracking-tight text-accent-ink">
              Sözleşme Analiz
            </span>
            <span className="hidden text-[11px] font-medium tracking-[0.14em] text-secondary-bright uppercase sm:inline">
              Asistanı
            </span>
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const active = item.match(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-t-md border-b-2 px-3 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "border-gold bg-accent-tint text-accent-ink"
                    : "border-transparent text-accent-ink-muted hover:bg-accent-tint/60 hover:text-accent-ink"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
