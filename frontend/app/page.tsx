"use client";

import { useCallback, useEffect, useState } from "react";
import { Scale } from "lucide-react";
import UploadDropzone from "@/components/UploadDropzone";
import DocumentList from "@/components/DocumentList";
import {
  deleteDocument,
  listDocuments,
  uploadDocuments,
  type DocumentSummary,
} from "@/lib/api";

export default function Home() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Belgeler yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleUpload(files: File[]) {
    setUploading(true);
    setError(null);
    try {
      const result = await uploadDocuments(files);
      if (result.failed.length > 0) {
        setError(
          result.failed
            .map((f) => `${f.filename ?? "Dosya"}: ${f.error}`)
            .join(" · "),
        );
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Yükleme başarısız oldu.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: string) {
    const previous = documents;
    setDocuments((docs) => docs.filter((d) => d.id !== id));
    try {
      await deleteDocument(id);
    } catch (err) {
      setDocuments(previous);
      setError(err instanceof Error ? err.message : "Silme işlemi başarısız oldu.");
    }
  }

  return (
    <div className="flex flex-1 justify-center">
      <main className="w-full max-w-2xl px-6 py-10 lg:max-w-4xl xl:max-w-5xl">
        <header className="mb-8">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold tracking-[0.14em] text-gold-hover uppercase">
            <Scale className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden />
            Sözleşme Yönetimi
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-balance text-ink">
            Sözleşmelerinizi yükleyin
          </h1>
          <p className="mt-2 max-w-lg text-[15px] leading-relaxed text-ink-2">
            Sözleşmenizi özetleyip olası riskli maddeleri işaretleriz, sorularınızı
            yanıtlarız — hepsi kendi bilgisayarınızda kalır, hiçbir belge dışarı çıkmaz.
          </p>
        </header>

        <UploadDropzone onUpload={handleUpload} uploading={uploading} />

        {error && (
          <p
            className="mt-4 rounded-lg px-4 py-3 text-sm"
            style={{ backgroundColor: "var(--status-critical-bg)", color: "var(--status-critical)" }}
          >
            {error}
          </p>
        )}

        <section className="mt-12">
          <h2 className="mb-4 text-xs font-semibold tracking-[0.14em] text-ink-3 uppercase">
            Yüklenen sözleşmeler
          </h2>
          {loading ? (
            <p className="text-sm text-ink-3">Yükleniyor…</p>
          ) : (
            <DocumentList documents={documents} onDelete={handleDelete} />
          )}
        </section>
      </main>
    </div>
  );
}
