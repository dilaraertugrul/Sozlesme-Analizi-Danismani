import type { DocumentDetail } from "@/lib/api";

export default function DocumentSummaryCard({ document }: { document: DocumentDetail }) {
  const hasFacts =
    document.value || document.effective_date || document.end_date || document.governing_law;
  const hasMeta =
    document.summary ||
    document.parties.length > 0 ||
    document.key_obligations.length > 0 ||
    hasFacts;

  if (!hasMeta) return null;

  return (
    <div className="card mb-6 p-6">
      {document.summary && <p className="text-sm leading-relaxed text-ink-2">{document.summary}</p>}

      {hasFacts && (
        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-border pt-4 text-sm sm:grid-cols-4">
          {document.value && (
            <div>
              <dt className="text-xs text-ink-3">Bedel</dt>
              <dd className="mt-0.5 text-ink-2">{document.value}</dd>
            </div>
          )}
          {document.effective_date && (
            <div>
              <dt className="text-xs text-ink-3">Başlangıç</dt>
              <dd className="mt-0.5 text-ink-2">{document.effective_date}</dd>
            </div>
          )}
          {document.end_date && (
            <div>
              <dt className="text-xs text-ink-3">Bitiş</dt>
              <dd className="mt-0.5 text-ink-2">{document.end_date}</dd>
            </div>
          )}
          {document.governing_law && (
            <div>
              <dt className="text-xs text-ink-3">Uygulanacak hukuk</dt>
              <dd className="mt-0.5 text-ink-2">{document.governing_law}</dd>
            </div>
          )}
        </dl>
      )}

      {document.parties.length > 0 && (
        <div className="mt-4 border-t border-border pt-4">
          <h3 className="text-xs font-medium tracking-wide text-ink-3 uppercase">Taraflar</h3>
          <ul className="mt-1.5 space-y-1 text-sm">
            {document.parties.map((party, i) => (
              <li key={i}>
                <span className="font-medium text-ink-2">{party.name}</span>{" "}
                <span className="text-ink-3">— {party.role}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {document.key_obligations.length > 0 && (
        <div className="mt-4 border-t border-border pt-4">
          <h3 className="text-xs font-medium tracking-wide text-ink-3 uppercase">
            Kilit yükümlülükler
          </h3>
          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-sm text-ink-2">
            {document.key_obligations.map((obligation, i) => (
              <li key={i}>{obligation}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
