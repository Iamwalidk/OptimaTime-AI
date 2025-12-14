import React, { useMemo, useState } from "react";

const HOURS = Array.from({ length: 15 }, (_, i) => i + 7); // 07 to 21

const formatTime = (dt) =>
  new Date(dt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

const ScheduleView = ({
  planDate,
  calendarDays,
  schedule,
  unscheduled,
  onFeedback,
  onReschedule,
  onDeleteItem,
}) => {
  const [openEvent, setOpenEvent] = useState(null);
  const [modalEdit, setModalEdit] = useState(null);

  // Build a week starting Monday of the current plan date
  const weekDays = useMemo(() => {
    const dateObj = new Date(planDate);
    const day = dateObj.getDay(); // 0=Sun
    const diffToMonday = day === 0 ? -6 : 1 - day;
    const monday = new Date(dateObj);
    monday.setDate(dateObj.getDate() + diffToMonday);
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      return d.toISOString().substring(0, 10);
    });
  }, [planDate]);

  // Map calendarDays to date string -> items
  const itemsByDate = useMemo(() => {
    const map = {};
    calendarDays.forEach((day) => {
      map[day.plan_date] = day.scheduled || [];
    });
    // overlay current day's live schedule to ensure latest state
    const currentDate = planDate;
    map[currentDate] = schedule;
    return map;
  }, [calendarDays, schedule, planDate]);

  const hoursHeight = 60; // px per hour for visual scale

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <p className="eyebrow">AI Planner</p>
          <h3>
            <span role="img" aria-label="ai">
              🤖
            </span>{" "}
            Week view
          </h3>
        </div>
      </div>

      <div className="week-calendar">
        <div className="week-hours">
          {HOURS.map((h) => (
            <div key={h} className="hour-label" style={{ height: hoursHeight }}>
              {`${h.toString().padStart(2, "0")}:00`}
            </div>
          ))}
        </div>
        <div className="week-grid">
          {weekDays.map((day) => {
            const items = itemsByDate[day] || [];
            return (
              <div key={day} className="week-day-column">
                <div className="week-day-header">
                  {new Date(day).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}
                </div>
                <div className="day-body">
                  <div className="day-lines">
                    {HOURS.map((h) => (
                      <div key={h} className="day-line" style={{ height: hoursHeight }}></div>
                    ))}
                  </div>
                  <div className="day-events">
                    {items.map((ev) => {
                      const start = new Date(ev.start);
                      const end = new Date(ev.end);
                      const startMinutes = start.getHours() * 60 + start.getMinutes();
                      const top = Math.max(0, (startMinutes - 7 * 60) * (hoursHeight / 60));
                      const durationMin = Math.max(30, (end - start) / 60000);
                      const height = (durationMin / 60) * hoursHeight;
                      return (
                        <div key={ev.plan_item_id || `${ev.task_id}-${ev.start}`} className="event-card" style={{ top, height }}>
                          <button
                            className="reason-btn"
                            title="Details & AI reasoning"
                            onClick={() => {
                              setOpenEvent(ev);
                              setModalEdit({
                                start: new Date(ev.start).toISOString().slice(0, 16),
                                end: new Date(ev.end).toISOString().slice(0, 16),
                              });
                            }}
                          >
                            ℹ️
                          </button>
                          <div className="event-title">{ev.title}</div>
                          <div className="event-time">
                            {formatTime(ev.start)} - {formatTime(ev.end)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="unscheduled-inline">
        <div className="card-header">
          <div>
            <p className="eyebrow">Unscheduled by AI</p>
            <h4>
              <span role="img" aria-label="warning">
                ⚠️
              </span>{" "}
              {unscheduled.length} tasks
            </h4>
            <p className="muted mini">These tasks remain in your backlog; the AI could not fit them today.</p>
          </div>
        </div>
        {unscheduled.length === 0 && <p className="muted">All tasks were placed.</p>}
        <ul className="list">
          {unscheduled.map((t) => (
            <li key={t.id} className="list-item">
              <div>
                <strong>{t.title}</strong>
                <p className="muted mini">{t.reason || "No available slot."}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {openEvent && (
        <div className="modal-overlay" onClick={() => setOpenEvent(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <div className="eyebrow">Task details</div>
                <h3>{openEvent.title}</h3>
                <p className="muted">
                  {formatTime(openEvent.start)} – {formatTime(openEvent.end)} ·{" "}
                  {new Date(openEvent.start).toLocaleDateString()}
                </p>
              </div>
              <button className="icon-btn" onClick={() => setOpenEvent(null)}>
                ×
              </button>
            </div>

            <div className="ai-explanation">
              <span className="ai-chip">AI reasoning</span>
              <p className="explanation">{openEvent.explanation}</p>
              {openEvent.llm_explanation && <p className="muted mini">{openEvent.llm_explanation}</p>}
            </div>

            <div className="inline mini" style={{ marginTop: "10px" }}>
              <button className="ghost" onClick={() => onFeedback({ taskId: openEvent.task_id, outcome: 1 })}>
                Prefer earlier
              </button>
              <button className="ghost" onClick={() => onFeedback({ taskId: openEvent.task_id, outcome: -1 })}>
                Prefer later
              </button>
            </div>

            {openEvent.plan_item_id && (
              <div className="edit-panel" style={{ marginTop: "12px" }}>
                <label>
                  <span>Start</span>
                  <input
                    type="datetime-local"
                    value={modalEdit?.start || new Date(openEvent.start).toISOString().slice(0, 16)}
                    onChange={(e) => setModalEdit((prev) => ({ ...(prev || {}), start: e.target.value }))}
                  />
                </label>
                <label>
                  <span>End</span>
                  <input
                    type="datetime-local"
                    value={modalEdit?.end || new Date(openEvent.end).toISOString().slice(0, 16)}
                    onChange={(e) => setModalEdit((prev) => ({ ...(prev || {}), end: e.target.value }))}
                  />
                </label>
                <div className="inline mini">
                  <button
                    onClick={() => {
                      onReschedule(openEvent.plan_item_id, modalEdit?.start || openEvent.start, modalEdit?.end || openEvent.end);
                      setOpenEvent(null);
                    }}
                  >
                    Save changes
                  </button>
                  <button className="ghost" onClick={() => onDeleteItem(openEvent.plan_item_id)}>
                    Remove from calendar
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ScheduleView;
