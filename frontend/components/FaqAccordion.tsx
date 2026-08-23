"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

export type FaqEntry = { question: string; answer: string };

export default function FaqAccordion({ items }: { items: FaqEntry[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className="flex flex-col gap-3">
      {items.map((item, i) => {
        const open = openIndex === i;
        return (
          <div key={item.question} className="card overflow-hidden">
            <button
              onClick={() => setOpenIndex(open ? null : i)}
              aria-expanded={open}
              className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left"
            >
              <span className="font-medium text-ink">{item.question}</span>
              <ChevronDown
                className={`h-4 w-4 shrink-0 text-ink-3 transition-transform ${open ? "rotate-180" : ""}`}
                strokeWidth={2}
                aria-hidden
              />
            </button>
            {open && (
              <div className="border-t border-border px-5 py-4 text-sm leading-relaxed text-ink-2">
                {item.answer}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
