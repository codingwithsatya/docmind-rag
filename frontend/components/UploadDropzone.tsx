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
    if (!file) {
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
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          hidden
          onChange={(event) => {
            handleFile(event.target.files?.[0]);
            event.target.value = "";
          }}
        />

        <div className="upload-icon">↑</div>

        <div className="upload-title" role="status" aria-live="polite">
          {uploading ? "Indexing document..." : "Upload PDF"}
        </div>

        <div className="upload-subtitle">Drag & drop or click to browse</div>
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
