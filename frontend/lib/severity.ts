import type { Severity } from "@/lib/api";

export const SEVERITY_ORDER: Severity[] = ["kritik", "yuksek", "orta", "dusuk", "bilgi"];

export const SEVERITY_LABEL: Record<Severity, string> = {
  kritik: "Kritik",
  yuksek: "Yüksek",
  orta: "Orta",
  dusuk: "Düşük",
  bilgi: "Bilgi",
};

// Backend 5 önem düzeyi kullanıyor, durum paleti 4 sabit rolden oluşuyor
// (good/warning/serious/critical); "dusuk" -> good, "bilgi" -> nötr gri.
export const SEVERITY_COLOR: Record<Severity, string> = {
  kritik: "var(--status-critical)",
  yuksek: "var(--status-serious)",
  orta: "var(--status-warning)",
  dusuk: "var(--status-good)",
  bilgi: "var(--status-muted)",
};

export const SEVERITY_BG: Record<Severity, string> = {
  kritik: "var(--status-critical-bg)",
  yuksek: "var(--status-serious-bg)",
  orta: "var(--status-warning-bg)",
  dusuk: "var(--status-good-bg)",
  bilgi: "var(--status-muted-bg)",
};

export function scoreColor(score: number): string {
  if (score >= 66) return "var(--status-critical)";
  if (score >= 45) return "var(--status-serious)";
  if (score >= 20) return "var(--status-warning)";
  return "var(--status-good)";
}
