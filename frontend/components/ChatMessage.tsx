"use client";

import { useState } from "react";

import type { Source } from "@/lib/types";

import SourceCard from "./SourceCard";
import SourceDrawer from "./SourceDrawer";

type ChatMessageProps = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  debugMode?: boolean;
  rewrittenQuery?: string;
};

export default function ChatMessage({
  role,
  content,
  sources = [],
  debugMode = false,
  rewrittenQuery,
}: ChatMessageProps) {
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);

  return (
    <>
      <div className={`chat-message chat-message--${role}`}>
        <div className="chat-message-label">
          {role === "user" ? "You" : "DocMind"}
        </div>

        <div className="chat-message-body">{content}</div>

        {role === "assistant" && debugMode && rewrittenQuery && (
          <div className="retrieval-debug">
            <div className="retrieval-debug__label">
              Rewritten retrieval query
            </div>

            <div className="retrieval-debug__query">{rewrittenQuery}</div>
          </div>
        )}

        {role === "assistant" && sources.length > 0 && (
          <div className="source-list">
            <div className="source-list-title">Sources</div>

            <div className="source-grid">
              {sources.map((source) => (
                <SourceCard
                  key={`${source.document_id}-${source.chunk_index}`}
                  source={source}
                  debugMode={debugMode}
                  onClick={() => setSelectedSource(source)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      <SourceDrawer
        source={selectedSource}
        debugMode={debugMode}
        onClose={() => setSelectedSource(null)}
      />
    </>
  );
}
