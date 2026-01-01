import React from "react";

const Topbar = ({ user, initials, onLogout }) => {
  return (
    <header className="topbar">
      <div className="top-left">
        <div className="brand-block">
          <div className="brand">
            OptimaTime <span className="brand-pill">AI</span>
          </div>
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
