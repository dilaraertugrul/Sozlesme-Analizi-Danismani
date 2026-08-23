import type { Severity } from "@/lib/api";
import { SEVERITY_BG, SEVERITY_COLOR, SEVERITY_LABEL } from "@/lib/severity";

type Props = { severity: Severity; count?: number };

export default function SeverityBadge({ severity, count }: Props) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium text-ink"
      style={{ backgroundColor: SEVERITY_BG[severity] }}
    >
      <span
        className="h-1.5 w-1.5 shrink-0 rounded-full"
        style={{ backgroundColor: SEVERITY_COLOR[severity] }}
        aria-hidden
      />
      {count !== undefined ? `${count} ${SEVERITY_LABEL[severity]}` : SEVERITY_LABEL[severity]}
    </span>
  );
}
