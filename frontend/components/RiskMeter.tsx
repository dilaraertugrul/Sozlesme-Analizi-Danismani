import type { Severity } from "@/lib/api";
import { SEVERITY_ORDER, scoreColor } from "@/lib/severity";
import SeverityBadge from "@/components/SeverityBadge";

type Props = {
  score: number;
  severityCounts: Record<Severity, number>;
  assessment: string;
};

export default function RiskMeter({ score, severityCounts, assessment }: Props) {
  const pct = Math.max(0, Math.min(100, score));
  const color = scoreColor(pct);

  return (
    <div className="card card-sealed overflow-hidden p-6">
      <p className="text-sm font-medium text-ink-3">Risk puanı</p>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-5xl font-semibold text-ink">{Math.round(pct)}</span>
        <span className="text-sm text-ink-3">/ 100</span>
      </div>

      <div
        className="mt-4 h-2.5 w-full overflow-hidden rounded-full"
        style={{ backgroundColor: "var(--chart-track)" }}
        role="meter"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>

      {assessment && <p className="mt-4 text-sm leading-relaxed text-ink-2">{assessment}</p>}

      <div className="mt-4 flex flex-wrap gap-2">
        {SEVERITY_ORDER.filter((s) => severityCounts[s] > 0).map((s) => (
          <SeverityBadge key={s} severity={s} count={severityCounts[s]} />
        ))}
      </div>
    </div>
  );
}
