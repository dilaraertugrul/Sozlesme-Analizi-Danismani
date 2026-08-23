export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8090";

export type Party = { name: string; role: string };

export type DocumentSummary = {
  id: string;
  filename: string;
  title: string;
  doc_type: string | null;
  parties: Party[];
  page_count: number;
  char_count: number;
  clause_count: number;
  risk_score: number | null;
  risk_count: number;
  analyzed: boolean;
  created_at: string;
};

export type UploadFailure = { filename: string | null; error: string };

export type UploadResponse = {
  uploaded: { id: string; title: string }[];
  failed: UploadFailure[];
};

export type Severity = "kritik" | "yuksek" | "orta" | "dusuk" | "bilgi";

export type FindingOption = { label: string; detail: string; impact: string };

export type Finding = {
  category: string;
  category_label: string;
  severity: Severity;
  severity_label: string;
  title: string;
  rationale: string;
  recommendation: string;
  options: FindingOption[];
  clause_ref: string | null;
  chunk_id: string | null;
  excerpt: string | null;
  rule_id: string | null;
  source: "kural" | "llm";
};

export type CategorySummary = {
  category: string;
  label: string;
  count: number;
  score: number;
  max_severity: Severity;
};

export type RiskAnalysis = {
  doc_id: string;
  risk_score: number;
  position: string;
  overall_assessment: string;
  severity_counts: Record<Severity, number>;
  categories: CategorySummary[];
  findings: Finding[];
  llm_error: string | null;
  analyzed_at: string;
};

export type DocumentClause = {
  id: string;
  ordinal: number;
  article_no: string | null;
  heading: string | null;
  label: string;
  text: string;
  page: number | null;
};

export type DocumentDetail = {
  id: string;
  filename: string;
  title: string;
  doc_type: string | null;
  parties: Party[];
  effective_date: string | null;
  end_date: string | null;
  governing_law: string | null;
  value: string | null;
  page_count: number;
  char_count: number;
  clause_count: number;
  risk_score: number | null;
  created_at: string;
  summary: string;
  key_obligations: string[];
  clauses: DocumentClause[];
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // yanıt gövdesi JSON değilse statusText ile devam edilir
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function listDocuments(): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>("/api/documents");
}

export function uploadDocuments(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  for (const file of files) formData.append("files", file);
  return request<UploadResponse>("/api/documents", {
    method: "POST",
    body: formData,
  });
}

export function deleteDocument(id: string): Promise<{ deleted: string }> {
  return request<{ deleted: string }>(`/api/documents/${id}`, {
    method: "DELETE",
  });
}

export function getDocument(id: string): Promise<DocumentDetail> {
  return request<DocumentDetail>(`/api/documents/${id}`);
}

export function getAnalysis(id: string): Promise<RiskAnalysis> {
  return request<RiskAnalysis>(`/api/documents/${id}/analysis`);
}

export function runAnalysis(
  id: string,
  options?: { use_llm?: boolean; perspective?: string | null },
): Promise<RiskAnalysis> {
  return request<RiskAnalysis>(`/api/documents/${id}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      use_llm: options?.use_llm ?? true,
      perspective: options?.perspective ?? null,
    }),
  });
}

export type CompareDocument = {
  id: string;
  title: string;
  doc_type: string | null;
  risk_score: number | null;
  parties: Party[];
};

export type RiskMatrixCell = {
  doc_id: string;
  severity: Severity | null;
  severity_label?: string;
  count: number;
  titles: string[];
  stance: "temiz" | "riskli";
};

export type RiskMatrixRow = {
  category: string;
  label: string;
  cells: RiskMatrixCell[];
};

export type CompareStance = "koruyucu" | "dengeli" | "riskli" | "duzenlenmemis";

export type CompareTopicCell = {
  doc_id: string;
  clause_ref: string | null;
  summary: string;
  stance: CompareStance;
};

export type CompareTopic = {
  topic: string;
  cells: CompareTopicCell[];
  verdict: string;
};

export type CompareResult = {
  documents: CompareDocument[];
  risk_matrix: RiskMatrixRow[];
  topic_labels: Record<string, string>;
  headline: string;
  topics: CompareTopic[];
  llm_error: string | null;
};

export function compareDocuments(
  docIds: string[],
  options?: { topics?: string[]; use_llm?: boolean },
): Promise<CompareResult> {
  return request<CompareResult>("/api/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      doc_ids: docIds,
      topics: options?.topics ?? null,
      use_llm: options?.use_llm ?? true,
    }),
  });
}

export type SuggestedQuestion = { question: string; category: string };

export function getSuggestedQuestions(id: string): Promise<{ questions: SuggestedQuestion[] }> {
  return request<{ questions: SuggestedQuestion[] }>(`/api/documents/${id}/suggested-questions`);
}

export type ChatCitation = {
  chunk_id: string;
  doc_id: string;
  doc_title: string;
  label: string;
  page: number | null;
  excerpt: string;
  score: number;
};

export type ChatHistoryItem = { role: "user" | "assistant"; content: string };

type StreamChatHandlers = {
  onCitations?: (citations: ChatCitation[]) => void;
  onDelta?: (text: string) => void;
  onError?: (message: string) => void;
};

export async function streamChat(
  params: {
    question: string;
    doc_ids?: string[] | null;
    history?: ChatHistoryItem[];
    top_k?: number;
  },
  handlers: StreamChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: params.question,
      doc_ids: params.doc_ids ?? null,
      history: params.history ?? [],
      top_k: params.top_k ?? 8,
    }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new ApiError(res.statusText, res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sepIndex: number;
    while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + 2);
      const line = rawEvent.startsWith("data: ") ? rawEvent.slice(6) : rawEvent;
      if (!line) continue;

      const event = JSON.parse(line) as
        | { type: "citations"; citations: ChatCitation[] }
        | { type: "delta"; text: string }
        | { type: "error"; message: string }
        | { type: "done" };

      if (event.type === "citations") handlers.onCitations?.(event.citations);
      else if (event.type === "delta") handlers.onDelta?.(event.text);
      else if (event.type === "error") handlers.onError?.(event.message);
    }
  }
}
