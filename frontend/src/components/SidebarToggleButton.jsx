import React from "react";

export default function SidebarToggleButton({ isOpen, onToggle }) {
  return (
    <button
      type="button"
      className={`sidebar-toggle ${isOpen ? "open" : ""}`}
      onClick={onToggle}
      aria-label={isOpen ? "Close sidebar" : "Open sidebar"}
      aria-expanded={isOpen}
    >
      <span className="sidebar-toggle-icon" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
    </button>
  );
}
