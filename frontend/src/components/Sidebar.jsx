import React from "react";

const Sidebar = ({
  user,
  initials,
  showSidebar,
  showInputPanel,
  showTasksPanel,
  showUnscheduledPanel,
  showNotesPanel,
  darkMode,
  onToggleSidebar,
  onToggleInput,
  onToggleTasks,
  onToggleUnscheduled,
  onToggleNotes,
  onToggleDarkMode,
}) => {
  if (!user) return null;

  return (
    <>
      {showSidebar && <div className="sidebar-overlay" onClick={onToggleSidebar}></div>}
      <aside className={`sidebar ${showSidebar ? "open" : ""}`}>
        <div className="sidebar-brand">Tools</div>
        <div className="sidebar-user">
          <div className="avatar">{initials || "U"}</div>
          <div>
            <div className="top-name">{user.name}</div>
            <div className="top-profile">{user.profile}</div>
          </div>
        </div>
        <div className="sidebar-buttons">
          <button className={showInputPanel ? "sidebar-btn active" : "sidebar-btn"} onClick={onToggleInput}>
            Input Layer
          </button>
          <button className={showTasksPanel ? "sidebar-btn active" : "sidebar-btn"} onClick={onToggleTasks}>
            Backlog Overview
          </button>
          <button
            className={showUnscheduledPanel ? "sidebar-btn active" : "sidebar-btn"}
            onClick={onToggleUnscheduled}
          >
            Unscheduled
          </button>
          <button className={showNotesPanel ? "sidebar-btn active" : "sidebar-btn"} onClick={onToggleNotes}>
            Notes
          </button>
          <button className={darkMode ? "sidebar-btn active" : "sidebar-btn"} onClick={onToggleDarkMode}>
            {darkMode ? "Light mode" : "Dark mode"}
          </button>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
