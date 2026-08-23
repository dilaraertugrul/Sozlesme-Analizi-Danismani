"use client";

import type { DocumentSummary } from "@/lib/api";

type Props = {
  documents: DocumentSummary[];
  selected: string[];
  onToggle: (id: string) => void;
  onClear: () => void;
};

export default function DocumentFilter({ documents, selected, onToggle, onClear }: Props) {
  if (documents.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      <button
        onClick={onClear}
        className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
          selected.length === 0
            ? "bg-accent text-white"
            : "bg-accent-soft text-ink-2 hover:bg-accent-soft/70"
        }`}
      >
        Tüm sözleşmeler
      </button>
      {documents.map((doc) => {
        const active = selected.includes(doc.id);
        return (
          <button
            key={doc.id}
            onClick={() => onToggle(doc.id)}
            className={`max-w-[220px] truncate rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
              active ? "bg-accent text-white" : "bg-accent-soft text-ink-2 hover:bg-accent-soft/70"
            }`}
            title={doc.title}
          >
            {doc.title}
          </button>
        );
      })}
    </div>
  );
}
