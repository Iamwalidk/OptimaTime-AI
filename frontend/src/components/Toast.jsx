import React from "react";

export default function Toast({ toast, onClose }) {
  if (!toast?.text) return null;

  const tone = toast.tone || "info";
  const stateClass = toast.closing ? "closing" : "open";

  return (
    <div className={`toast ${tone} ${stateClass}`} role="status" aria-live="polite">
      <div className="toast-text">{toast.text}</div>
      <button type="button" className="toast-close" onClick={onClose} aria-label="Close">
        ✕
      </button>
    </div>
  );
}
