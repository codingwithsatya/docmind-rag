"use client";

type QuestionInputProps = {
  value: string;
  asking: boolean;
  disabled: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export default function QuestionInput({
  value,
  asking,
  disabled,
  onChange,
  onSubmit,
}: QuestionInputProps) {
  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();

      if (!disabled && !asking && value.trim()) {
        onSubmit();
      }
    }
  }

  return (
    <div className="question-composer">
      <div className="composer-icon">✦</div>

      <textarea
        value={value}
        disabled={disabled}
        rows={1}
        placeholder={
          disabled
            ? "Upload a PDF to start..."
            : "Ask anything about your document..."
        }
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
      />

      <div className="composer-actions">
        <span className="enter-hint">↵</span>

        <button
          type="button"
          className="send-button"
          disabled={disabled || asking || !value.trim()}
          onClick={onSubmit}
          aria-label="Ask DocMind"
        >
          {asking ? <span className="thinking-dot">•••</span> : "↑"}
        </button>
      </div>
    </div>
  );
}
