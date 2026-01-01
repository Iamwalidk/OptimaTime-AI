import React from "react";

const Toast = ({ toast, onClose }) => {
  if (!toast.text) return null;

  return (
    <div
      className={`toast ${toast.tone} ${toast.closing ? "closing" : "open"}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <span className="toast-text">{toast.text}</span>
      <button type="button" className="toast-close" onClick={onClose} aria-label="Close notification">
        x
      </button>
    </div>
  );
};

export default Toast;
