"use client";

import type { IngestResponse } from "@/lib/types";

import UploadDropzone from "./UploadDropzone";

type DocumentSidebarProps = {
  document: IngestResponse | null;
  uploading: boolean;
  onUpload: (file: File) => void;
};

export default function DocumentSidebar({
  document,
  uploading,
  onUpload,
}: DocumentSidebarProps) {
  return (
    <div className="document-sidebar">
      <div className="brand-block">
        <div className="brand-mark">D</div>

        <div>
          <h1 className="brand-title">DocMind</h1>

          <p className="brand-subtitle">RAG Document AI</p>
        </div>
      </div>

      <UploadDropzone uploading={uploading} onUpload={onUpload} />

      <div className="sidebar-section">
        <div className="sidebar-section-title">Documents</div>

        {!document && (
          <div className="empty-document">No document uploaded yet.</div>
        )}

        {document && (
          <div className="document-card">
            <div className="document-icon">PDF</div>

            <div className="document-details">
              <div className="document-name">{document.filename}</div>

              <div className="document-status">
                <span className="status-dot" />

                {document.status === "already_exists"
                  ? "Already indexed"
                  : "Ready"}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
