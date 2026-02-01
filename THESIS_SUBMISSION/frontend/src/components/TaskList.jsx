import React from "react";

const TaskList = ({ tasks }) => {
  return (
    <div className="card list-card">
      {tasks.length === 0 && <p className="muted">No tasks yet.</p>}
      <ul className="list">
        {tasks.map((t) => (
          <li key={t.id} className="list-item">
            <div>
              <strong>{t.title}</strong>
              <p className="muted">
                {t.task_type} · {t.importance} · {t.duration_minutes} min
              </p>
            </div>
            <span className={`status status-${t.status}`}>{t.status}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default TaskList;
