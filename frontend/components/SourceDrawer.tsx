"use client";

import type { Source } from "@/lib/types";
import { useEffect, useState } from "react";

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
  const [viewMode, setViewMode] = useState<"readable" | "original">(
    "readable"
  );

  const readableContent = source?.content
    .replace(/\s+/g, " ")
    .trim();

  useEffect(() => {
    if (!source) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [source, onClose]);

  if (!source) {
    return null;
  }

  return (
    <div
      className="source-drawer-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="source-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={`Source details — Page ${source.page_number}`}
      >
        <div className="source-drawer-header">
          <div>
            <div className="source-drawer-label">SOURCE</div>

            <h3>Page {source.page_number}</h3>
          </div>

          <button
            type="button"
            className="source-drawer-close"
            onClick={onClose}
            aria-label="Close source details"
          >
            ✕
          </button>
        </div>

        <div
          className="source-view-toggle"
          role="group"
          aria-label="Source text display mode"
        >
          <button
            type="button"
            className={viewMode === "readable" ? "active" : ""}
            aria-pressed={viewMode === "readable"}
            onClick={() => setViewMode("readable")}
          >
            Readable
          </button>

          <button
            type="button"
            className={viewMode === "original" ? "active" : ""}
            aria-pressed={viewMode === "original"}
            onClick={() => setViewMode("original")}
          >
            Original
          </button>
        </div>

        <div
          className={`source-drawer-content ${viewMode === "readable" ? "source-drawer-content--readable" : ""
            }`}
        >
          {viewMode === "readable" ? readableContent : source.content}
        </div>

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
