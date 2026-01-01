import React from "react";

const SidebarToggleButton = ({ isOpen, onToggle }) => {
  return (
    <button
      type="button"
      className={`sidebar-toggle ${isOpen ? "open" : ""}`}
      onClick={onToggle}
      aria-label={isOpen ? "Close menu" : "Open menu"}
      aria-expanded={isOpen}
      aria-controls="app-sidebar"
    >
      <span className="sidebar-toggle-icon" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </span>
    </button>
  );
};

export default SidebarToggleButton;
