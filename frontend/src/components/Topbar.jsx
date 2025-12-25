import React from "react";

const Topbar = ({ user, initials, onToggleSidebar, onLogout }) => {
  return (
    <header className="topbar">
      <div className="top-left">
        {user && (
          <button className="hamburger" onClick={onToggleSidebar}>
            <span></span>
            <span></span>
            <span></span>
          </button>
        )}
        <div className="brand-block">
          <div className="brand">OptimaTime AI</div>
          <div className="brand-sub">Powered by a trained priority model + adaptive scheduling.</div>
        </div>
      </div>
      {user && (
        <div className="top-actions">
          <div className="avatar">{initials || "U"}</div>
          <div className="top-user">
            <div className="top-name">{user.name}</div>
            <div className="top-profile">{user.profile}</div>
          </div>
          <button className="ghost" onClick={onLogout}>
            Sign out
          </button>
        </div>
      )}
    </header>
  );
};

export default Topbar;
