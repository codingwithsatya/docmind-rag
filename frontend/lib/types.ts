export type IngestResponse = {
  document_id: string;
  filename: string;
  chunk_count?: number;
  status: "ingested" | "already_exists";
};

export type Source = {
  document_id: string;
  page_number: number;
  chunk_index: number;
  similarity: number;
  content: string;
};

export type AskResponse = {
  document_id: string;
  question: string;
  answer: string;
  rewritten_query: string;
  sources: Source[];
};

export type ChatTurn = {
  id: string;
  question: string;
  answer: string;
  rewritten_query: string;
  sources: Source[];
};
