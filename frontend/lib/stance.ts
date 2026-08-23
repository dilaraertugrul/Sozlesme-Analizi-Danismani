import type { CompareStance } from "@/lib/api";

export const STANCE_LABEL: Record<CompareStance, string> = {
  koruyucu: "Koruyucu",
  dengeli: "Dengeli",
  riskli: "Riskli",
  duzenlenmemis: "Düzenlenmemiş",
};

export const STANCE_COLOR: Record<CompareStance, string> = {
  koruyucu: "var(--status-good)",
  dengeli: "var(--status-muted)",
  riskli: "var(--status-critical)",
  duzenlenmemis: "var(--status-warning)",
};

export const STANCE_BG: Record<CompareStance, string> = {
  koruyucu: "var(--status-good-bg)",
  dengeli: "var(--status-muted-bg)",
  riskli: "var(--status-critical-bg)",
  duzenlenmemis: "var(--status-warning-bg)",
};
