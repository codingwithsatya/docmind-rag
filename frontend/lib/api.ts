import type { AskResponse, ChatTurn, IngestResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function errorMessage(response: Response, fallback: string) {
  try {
    const body: unknown = await response.json();

    if (
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof body.detail === "string"
    ) {
      return body.detail;
    }
  } catch {
    // Use the stable fallback when a proxy or server returns a non-JSON error.
  }

  return fallback;
}

export async function ingestDocument(file: File): Promise<IngestResponse> {
  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch(`${API_URL}/documents/ingest`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(
      await errorMessage(response, "Could not upload the PDF. Please try again."),
    );
  }

  return response.json();
}

export async function askDocument(
  documentId: string,
  question: string,
  messages: ChatTurn[],
): Promise<AskResponse> {
  const history = messages.slice(-3).map((message) => ({
    question: message.question,
    answer: message.answer,
  }));

  const response = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      document_id: documentId,
      question,
      history,
    }),
  });

  if (!response.ok) {
    throw new Error(
      await errorMessage(response, "Could not answer the question. Please try again."),
    );
  }

  return response.json();
}
