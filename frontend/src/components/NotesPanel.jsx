import React from "react";

const NotesPanel = ({ isOpen, noteDraft, notes, onDraftChange, onAddNote, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="flyout">
      <div className="flyout-header">
        <h4>Notes</h4>
        <button className="icon-btn" onClick={onClose}>
          x
        </button>
      </div>
      <div className="form-grid">
        <label>
          <span>Title</span>
          <input
            type="text"
            value={noteDraft.title}
            onChange={(e) => onDraftChange({ ...noteDraft, title: e.target.value })}
          />
        </label>
        <label>
          <span>Body</span>
          <textarea
            rows={3}
            value={noteDraft.body}
            onChange={(e) => onDraftChange({ ...noteDraft, body: e.target.value })}
          />
        </label>
        <button onClick={onAddNote} disabled={!noteDraft.title}>
          Save note
        </button>
      </div>
      <div className="list">
        {notes.length === 0 && <p className="muted">No notes yet.</p>}
        {notes.map((n) => (
          <div key={n.id} className="list-item">
            <div>
              <strong>{n.title}</strong>
              <p className="muted">{new Date(n.created_at).toLocaleString()}</p>
              {n.body && <p className="muted">{n.body}</p>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default NotesPanel;
