"use client";

import type { Source } from "@/lib/types";

type SourceDrawerProps = {
  source: Source | null;
  debugMode: boolean;
  onClose: () => void;
};

export default function SourceDrawer({
  source,
  debugMode,
  onClose,
}: SourceDrawerProps) {
  if (!source) {
    return null;
  }

  return (
    <div className="source-drawer-backdrop">
      <div className="source-drawer">
        <div className="source-drawer-header">
          <div>
            <div className="source-drawer-label">SOURCE</div>

            <h3>Page {source.page_number}</h3>
          </div>

          <button
            type="button"
            className="source-drawer-close"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        <div className="source-drawer-content">{source.content}</div>

        {debugMode && (
          <div className="source-drawer-meta">
            <div>
              <span>Chunk</span>
              <strong>{source.chunk_index}</strong>
            </div>

            <div>
              <span>Similarity</span>
              <strong>{(source.similarity * 100).toFixed(1)}%</strong>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
