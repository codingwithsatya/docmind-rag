"use client";

import { useRef, useState } from "react";

type UploadDropzoneProps = {
  uploading: boolean;
  onUpload: (file: File) => void;
};

export default function UploadDropzone({
  uploading,
  onUpload,
}: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [dragging, setDragging] = useState(false);

  function handleFile(file?: File) {
    if (!file) {
      return;
    }

    if (file.type !== "application/pdf") {
      alert("Please upload a PDF file.");

      return;
    }

    onUpload(file);
  }

  return (
    <div
      className={`upload-dropzone ${dragging ? "upload-dropzone--active" : ""}`}
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
        onChange={(event) => handleFile(event.target.files?.[0])}
      />

      <div className="upload-icon">↑</div>

      <div className="upload-title">
        {uploading ? "Indexing document..." : "Upload PDF"}
      </div>

      <div className="upload-subtitle">Drag & drop or click to browse</div>
    </div>
  );
}
