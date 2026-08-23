import type { CategorySummary } from "@/lib/api";
import { SEVERITY_COLOR } from "@/lib/severity";
import SeverityBadge from "@/components/SeverityBadge";

export default function CategoryBarChart({ categories }: { categories: CategorySummary[] }) {
  if (categories.length === 0) return null;

  return (
    <div className="card p-6">
      <h3 className="text-sm font-medium text-ink-3">Kategoriye göre risk yoğunluğu</h3>
      <div className="mt-4 flex flex-col gap-4">
        {categories.map((cat) => (
          <div key={cat.category} className="space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-sm font-medium text-ink-2">
                {cat.label} <span className="font-normal text-ink-3">· {cat.count} bulgu</span>
              </span>
              <SeverityBadge severity={cat.max_severity} />
            </div>
            <div className="flex items-center gap-3">
              <div
                className="h-5 flex-1 overflow-hidden rounded-full"
                style={{ backgroundColor: "var(--chart-track)" }}
              >
                <div
                  className="h-full"
                  style={{
                    width: `${Math.max(0, Math.min(100, cat.score))}%`,
                    backgroundColor: SEVERITY_COLOR[cat.max_severity],
                    borderRadius: "0 9999px 9999px 0",
                  }}
                />
              </div>
              <span className="w-8 shrink-0 text-right text-sm text-ink-2">
                {Math.round(cat.score)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
