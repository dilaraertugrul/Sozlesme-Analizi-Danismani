"use client";

import { useRef, useState, type DragEvent } from "react";

const ACCEPTED_SUFFIXES = [".pdf", ".docx", ".txt", ".md"];

type Props = {
  onUpload: (files: File[]) => Promise<void>;
  uploading: boolean;
};

export default function UploadDropzone({ onUpload, uploading }: Props) {
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    void onUpload(Array.from(fileList));
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragActive(false);
    handleFiles(event.dataTransfer.files);
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragActive(true);
      }}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={handleDrop}
      onClick={() => !uploading && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      aria-disabled={uploading}
      className={`flex flex-col items-center justify-center gap-2.5 rounded-xl border-2 border-dashed px-6 py-9 text-center transition-colors ${
        uploading
          ? "cursor-not-allowed border-border bg-surface/60"
          : isDragActive
            ? "cursor-pointer border-accent bg-accent-soft"
            : "cursor-pointer border-accent/50 bg-surface hover:border-accent hover:bg-accent-soft/60"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED_SUFFIXES.join(",")}
        className="hidden"
        disabled={uploading}
        onChange={(event) => {
          handleFiles(event.target.files);
          event.target.value = "";
        }}
      />
      <svg
        className="h-7 w-7 text-gold"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.4}
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 7.5L12 3m0 0L7.5 7.5M12 3v13.5"
        />
      </svg>
      <div>
        <p className="font-medium text-ink">
          {uploading
            ? "Yükleniyor…"
            : "Sözleşmeleri buraya sürükleyin ya da tıklayarak seçin"}
        </p>
        <p className="mt-1 text-sm text-ink-3">
          Desteklenen türler: {ACCEPTED_SUFFIXES.join(", ")} · birden fazla dosya seçilebilir
        </p>
      </div>
      {!uploading && (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            inputRef.current?.click();
          }}
          className="mt-1 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-accent-hover hover:shadow-md"
        >
          Dosya seç
        </button>
      )}
    </div>
  );
}
