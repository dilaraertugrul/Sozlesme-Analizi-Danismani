import type { CompareStance } from "@/lib/api";
import { STANCE_BG, STANCE_COLOR, STANCE_LABEL } from "@/lib/stance";

export default function StanceBadge({ stance }: { stance: CompareStance }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium text-ink"
      style={{ backgroundColor: STANCE_BG[stance] }}
    >
      <span
        className="h-1.5 w-1.5 shrink-0 rounded-full"
        style={{ backgroundColor: STANCE_COLOR[stance] }}
        aria-hidden
      />
      {STANCE_LABEL[stance]}
    </span>
  );
}
