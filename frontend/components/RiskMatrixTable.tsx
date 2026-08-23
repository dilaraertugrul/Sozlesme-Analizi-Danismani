import type { CompareDocument, RiskMatrixRow } from "@/lib/api";
import SeverityBadge from "@/components/SeverityBadge";

export default function RiskMatrixTable({
  documents,
  rows,
}: {
  documents: CompareDocument[];
  rows: RiskMatrixRow[];
}) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-ink-3">
        Karşılaştırılacak risk bulgusu yok — sözleşmeler henüz analiz edilmemiş olabilir.
      </p>
    );
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="px-4 py-2.5 text-left font-medium text-ink-3">Kategori</th>
            {documents.map((doc) => (
              <th
                key={doc.id}
                className="max-w-[160px] truncate px-4 py-2.5 text-left font-medium text-ink-3"
                title={doc.title}
              >
                {doc.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.category} className="border-b border-border last:border-0">
              <td className="px-4 py-3 font-medium text-ink-2">{row.label}</td>
              {documents.map((doc) => {
                const cell = row.cells.find((c) => c.doc_id === doc.id);
                if (!cell || !cell.severity) {
                  return (
                    <td key={doc.id} className="px-4 py-3">
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium text-ink"
                        style={{ backgroundColor: "var(--status-good-bg)" }}
                      >
                        <span
                          className="h-1.5 w-1.5 shrink-0 rounded-full"
                          style={{ backgroundColor: "var(--status-good)" }}
                          aria-hidden
                        />
                        Temiz
                      </span>
                    </td>
                  );
                }
                return (
                  <td key={doc.id} className="px-4 py-3" title={cell.titles.join("; ")}>
                    <div className="flex items-center gap-1.5">
                      <SeverityBadge severity={cell.severity} />
                      {cell.count > 1 && <span className="text-xs text-ink-3">×{cell.count}</span>}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
