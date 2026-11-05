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

  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);

  const [mobileDocumentsOpen, setMobileDocumentsOpen] = useState(false);

  const [debugMode, setDebugMode] = useState(false);

  const [uploadError, setUploadError] = useState<string | null>(null);

  const [questionError, setQuestionError] = useState<string | null>(null);

  async function handleUpload(file: File) {
    try {
      setUploading(true);
      setUploadError(null);

      const result = await ingestDocument(file);

      setDocument(result);
      setMessages([]);
      setQuestion("");
      setUploadError(null);
    } catch (error) {
      setUploadError(
        error instanceof Error
          ? error.message
          : "Could not upload the PDF. Please try again.",
      );
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
      setPendingQuestion(currentQuestion);
      setQuestionError(null);
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
      setQuestionError(null);
    } catch (error) {
      setQuestion(currentQuestion);
      setQuestionError(
        error instanceof Error
          ? error.message
          : "Could not answer the question. Please try again.",
      );
    } finally {
      setPendingQuestion(null);
      setAsking(false);
    }
  }

  return (
    <AppShell
      mobileOpen={mobileDocumentsOpen}
      onMobileOpenChange={setMobileDocumentsOpen}
      sidebar={
        <DocumentSidebar
          document={document}
          uploading={uploading}
          error={uploadError}
          onUpload={handleUpload}
          onUploadError={setUploadError}
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
        error={questionError}
        onDebugToggle={() => setDebugMode((current) => !current)}
        onQuestionChange={setQuestion}
        onAsk={handleAsk}
        pendingQuestion={pendingQuestion}
        onOpenDocuments={() => {
          if (window.matchMedia("(max-width: 850px)").matches) {
            setMobileDocumentsOpen(true);
          } else {
            window.document
              .getElementById("docmind-pdf-upload")
              ?.click();
          }
        }}
      />
    </AppShell>
  );
}
