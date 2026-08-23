import type { CompareDocument, CompareTopic } from "@/lib/api";
import StanceBadge from "@/components/StanceBadge";

export default function CompareTopicCard({
  topic,
  documents,
}: {
  topic: CompareTopic;
  documents: CompareDocument[];
}) {
  const docTitle = (id: string) => documents.find((d) => d.id === id)?.title ?? id;

  return (
    <div className="card p-5">
      <h3 className="font-medium text-ink">{topic.topic}</h3>
      {topic.verdict && <p className="mt-1 text-sm text-ink-2">{topic.verdict}</p>}
      <ul className="mt-3 space-y-2.5">
        {topic.cells.map((cell) => (
          <li key={cell.doc_id} className="rounded-lg bg-paper px-3 py-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-medium text-ink-2">
                {docTitle(cell.doc_id)}
                {cell.clause_ref ? ` · ${cell.clause_ref}` : ""}
              </span>
              <StanceBadge stance={cell.stance} />
            </div>
            <p className="mt-1 text-sm text-ink-2">{cell.summary}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
