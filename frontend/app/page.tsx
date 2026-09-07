"use client";

import { useState } from "react";

import AppShell from "@/components/AppShell";
import ChatPanel from "@/components/ChatPanel";
import DocumentSidebar from "@/components/DocumentSidebar";

import { askDocument, ingestDocument } from "@/lib/api";

import type { ChatTurn, IngestResponse } from "@/lib/types";

export default function Home() {
  const [document, setDocument] = useState<IngestResponse | null>(null);

  const [question, setQuestion] = useState("");

  const [messages, setMessages] = useState<ChatTurn[]>([]);

  const [uploading, setUploading] = useState(false);

  const [asking, setAsking] = useState(false);

  const [debugMode, setDebugMode] = useState(false);

  async function handleUpload(file: File) {
    try {
      setUploading(true);

      const result = await ingestDocument(file);

      setDocument(result);
      setMessages([]);
      setQuestion("");
    } catch (error) {
      console.error(error);
    } finally {
      setUploading(false);
    }
  }

  async function handleAsk() {
    if (!document || !question.trim()) {
      return;
    }

    const currentQuestion = question;

    try {
      setAsking(true);
      setQuestion("");

      const result = await askDocument(
        document.document_id,
        currentQuestion,
        messages,
      );

      const newMessage: ChatTurn = {
        id: crypto.randomUUID(),
        question: currentQuestion,
        answer: result.answer,
        rewritten_query: result.rewritten_query,
        sources: result.sources,
      };

      setMessages((current) => [...current, newMessage]);
    } catch (error) {
      console.error(error);
      setQuestion(currentQuestion);
    } finally {
      setAsking(false);
    }
  }

  return (
    <AppShell
      sidebar={
        <DocumentSidebar
          document={document}
          uploading={uploading}
          onUpload={handleUpload}
        />
      }
    >
      <ChatPanel
        messages={messages}
        question={question}
        asking={asking}
        disabled={!document}
        documentName={document?.filename}
        debugMode={debugMode}
        onDebugToggle={() => setDebugMode((current) => !current)}
        onQuestionChange={setQuestion}
        onAsk={handleAsk}
      />
    </AppShell>
  );
}
