"use client";

import { useRef, useState } from "react";

type UploadDropzoneProps = {
  uploading: boolean;
  error: string | null;
  onUpload: (file: File) => void;
  onUploadError: (message: string) => void;
};

export default function UploadDropzone({
  uploading,
  error,
  onUpload,
  onUploadError,
}: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [dragging, setDragging] = useState(false);

  function handleFile(file?: File) {
    if (!file || uploading) {
      return;
    }

    if (file.type !== "application/pdf") {
      onUploadError("Please upload a PDF file.");

      return;
    }

    onUpload(file);
  }

  return (
    <>
      <div
        className={`upload-dropzone ${dragging ? "upload-dropzone--active" : ""}`}
        aria-busy={uploading}
        aria-describedby={error ? "upload-error" : undefined}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();

          setDragging(false);

          handleFile(event.dataTransfer.files?.[0]);
        }}
        onClick={() => {
          if (!uploading) {
            inputRef.current?.click();
          }
        }}
      >
        <input
          id="docmind-pdf-upload"
          ref={inputRef}
          type="file"
          accept="application/pdf"
          hidden
          onChange={(event) => {
            handleFile(event.target.files?.[0]);
            event.target.value = "";
          }}
          disabled={uploading}
        />

        <div className="upload-icon">
          {uploading ? (
            <span className="upload-spinner" aria-hidden="true" />
          ) : (
            <span aria-hidden="true">↑</span>
          )}
        </div>

        <div className="upload-title" role="status" aria-live="polite">
          {uploading ? "Indexing document..." : "Upload PDF"}
        </div>

        <div className="upload-subtitle">
          {uploading
            ? "Preparing your PDF for AI-powered search"
            : "Drag & drop or click to browse"}
        </div>
      </div>

      {error && (
        <div
          id="upload-error"
          className="inline-error inline-error--sidebar"
          role="alert"
        >
          {error}
        </div>
      )}
    </>
  );
}
