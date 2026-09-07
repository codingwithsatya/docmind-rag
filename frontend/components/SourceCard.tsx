"use client";

import type { Source } from "@/lib/types";

type SourceCardProps = {
  source: Source;
  debugMode: boolean;
  onClick: () => void;
};

export default function SourceCard({
  source,
  debugMode,
  onClick,
}: SourceCardProps) {
  return (
    <button type="button" className="source-card" onClick={onClick}>
      <div className="source-page">📄 Page {source.page_number}</div>

      {debugMode ? (
        <div className="source-meta">
          Chunk {source.chunk_index}
          {" · "}
          {(source.similarity * 100).toFixed(1)}%
        </div>
      ) : (
        <div className="source-meta">View source</div>
      )}
    </button>
  );
}
