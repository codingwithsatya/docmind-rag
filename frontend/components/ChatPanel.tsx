"use client";

import type { ChatTurn } from "@/lib/types";

import ChatMessage from "./ChatMessage";
import QuestionInput from "./QuestionInput";

type ChatPanelProps = {
  messages: ChatTurn[];
  question: string;
  asking: boolean;
  disabled: boolean;
  documentName?: string;
  debugMode: boolean;
  error: string | null;
  onDebugToggle: () => void;
  onQuestionChange: (value: string) => void;
  onAsk: () => void;
  pendingQuestion: string | null;
  onOpenDocuments: () => void;
};

const suggestions = [
  "Summarize this document",
  "What are the key points?",
  "What experience is mentioned?",
  "What are the important dates?",
];

export default function ChatPanel({
  messages,
  question,
  asking,
  disabled,
  documentName,
  debugMode,
  error,
  onDebugToggle,
  onQuestionChange,
  onAsk,
  pendingQuestion,
  onOpenDocuments,
}: ChatPanelProps) {
  return (
    <div className="chat-panel">
      <header className="workspace-header">
        <div className="workspace-document">
          <div className="workspace-file-icon">PDF</div>

          <div>
            <div className="workspace-label">CURRENT DOCUMENT</div>

            <div className="workspace-file-name">
              {documentName ?? "No document selected"}
            </div>
          </div>
        </div>

        <div className="workspace-actions">
          <div className="grounded-badge">
            <span className="grounded-dot" />
            Grounded RAG
          </div>

          <button
            type="button"
            className={`debug-button ${debugMode ? "debug-button--active" : ""
              }`}
            onClick={onDebugToggle}
          >
            <span className="debug-status-dot" />
            Debug
          </button>
        </div>
      </header>

      <div className="chat-content">
        {messages.length === 0 && !pendingQuestion && (
          <div className="hero">
            <div className="hero-orb">
              <span>✦</span>
            </div>

            <div className="hero-eyebrow">DOCUMENT INTELLIGENCE</div>

            <h1>
              Ask your document
              <span> anything.</span>
            </h1>

            <p className="hero-description">
              Get grounded answers directly from your PDF, backed by semantic
              retrieval and page-level sources.
            </p>

            {!disabled && (
              <div className="suggestion-section">
                <div className="suggestion-label">TRY ASKING</div>

                <div className="suggestion-grid">
                  {suggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      className="suggestion-card"
                      onClick={() => onQuestionChange(suggestion)}
                    >
                      <span className="suggestion-spark">✦</span>

                      <span>{suggestion}</span>

                      <span className="suggestion-arrow">→</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {disabled && (
              <button
                type="button"
                className="hero-upload-hint"
                onClick={onOpenDocuments}
              >
                <span aria-hidden="true">↑</span>
                Upload a PDF to get started
              </button>
            )}
          </div>
        )}

        {(messages.length > 0 || pendingQuestion) && (
          <div className="conversation">
            {messages.map((message) => (
              <div key={message.id}>
                <ChatMessage role="user" content={message.question} />

                <ChatMessage
                  role="assistant"
                  content={message.answer}
                  sources={message.sources}
                  debugMode={debugMode}
                  rewrittenQuery={message.rewritten_query}
                />
              </div>
            ))}

            {pendingQuestion && (
              <ChatMessage
                role="user"
                content={pendingQuestion}
              />
            )}

            {asking && (
              <div className="assistant-thinking" role="status" aria-live="polite">
                <span />
                <span />
                <span />
                DocMind is searching your document...
              </div>
            )}
          </div>
        )}
      </div>

      <div className="chat-input-wrap">
        {error && (
          <div className="inline-error inline-error--question" role="alert">
            {error}
          </div>
        )}

        <QuestionInput
          value={question}
          asking={asking}
          disabled={disabled}
          onChange={onQuestionChange}
          onSubmit={onAsk}
        />

        <div className="composer-caption">
          DocMind answers using retrieved document context. Verify important
          information against the source.
        </div>
      </div>
    </div>
  );
}
