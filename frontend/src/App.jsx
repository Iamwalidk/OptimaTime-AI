import React, { useCallback, useEffect, useMemo, useState } from "react";
import LoginForm from "./components/LoginForm";
import NotesPanel from "./components/NotesPanel";
import Sidebar from "./components/Sidebar";
import TaskForm from "./components/TaskForm";
import TaskList from "./components/TaskList";
import Topbar from "./components/Topbar";
import ScheduleView from "./components/ScheduleView";
import { useAuth } from "./hooks/useAuth";
import { useNotes } from "./hooks/useNotes";
import { usePlanning } from "./hooks/usePlanning";
import { useTasks } from "./hooks/useTasks";

const App = () => {
  const [toast, setToast] = useState({ text: "", tone: "info" });
  const [darkMode, setDarkMode] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);
  const [showInputPanel, setShowInputPanel] = useState(false);
  const [showTasksPanel, setShowTasksPanel] = useState(false);
  const [showUnscheduledPanel, setShowUnscheduledPanel] = useState(false);
  const [showNotesPanel, setShowNotesPanel] = useState(false);

  const showToast = useCallback((text, tone = "info") => setToast({ text, tone }), []);

  const closeFlyouts = useCallback(() => {
    setShowInputPanel(false);
    setShowTasksPanel(false);
    setShowUnscheduledPanel(false);
    setShowNotesPanel(false);
  }, []);

  const { user, authLoading, handleAuth, logout } = useAuth({
    onSessionExpired: () => {
      closeFlyouts();
      setShowSidebar(false);
    },
    showToast,
  });

  const { tasks, tasksLoading, refreshTasks, handleTaskCreate } = useTasks({ user, showToast });
  const planning = usePlanning({ user, showToast, refreshTasks });
  const notes = useNotes({ user, showToast });

  useEffect(() => {
    if (user && showNotesPanel) {
      notes.refreshNotes();
    }
  }, [user, showNotesPanel, notes.refreshNotes]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  const anyFlyoutOpen = useMemo(
    () => showInputPanel || showTasksPanel || showUnscheduledPanel || showNotesPanel,
    [showInputPanel, showTasksPanel, showUnscheduledPanel, showNotesPanel]
  );
  const flyoutWidth = anyFlyoutOpen ? 380 : 0;
  const sidebarWidth = showSidebar ? 240 : 0;

  const initials = user?.name ? user.name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase() : "";
  const pendingCount = useMemo(
    () => tasks.filter((t) => t.status === "pending" || t.status === "unscheduled").length,
    [tasks]
  );

  return (
    <div className="app-shell">
      <Topbar
        user={user}
        initials={initials}
        onToggleSidebar={() => setShowSidebar((v) => !v)}
        onLogout={() => {
          logout();
          closeFlyouts();
          setShowSidebar(false);
        }}
      />

      {!user && (
        <section className="auth-wrapper">
          <LoginForm onLoggedIn={handleAuth} loading={authLoading} />
        </section>
      )}

      {user && (
        <div className={`app-layout ${anyFlyoutOpen ? "flyouts-open" : ""}`}>
          <Sidebar
            user={user}
            initials={initials}
            showSidebar={showSidebar}
            showInputPanel={showInputPanel}
            showTasksPanel={showTasksPanel}
            showUnscheduledPanel={showUnscheduledPanel}
            showNotesPanel={showNotesPanel}
            darkMode={darkMode}
            onToggleSidebar={() => setShowSidebar((v) => !v)}
            onToggleInput={() => setShowInputPanel((v) => !v)}
            onToggleTasks={() => setShowTasksPanel((v) => !v)}
            onToggleUnscheduled={() => setShowUnscheduledPanel((v) => !v)}
            onToggleNotes={() => setShowNotesPanel((v) => !v)}
            onToggleDarkMode={() => setDarkMode((d) => !d)}
          />

          <main
            className="main-area"
            style={{
              marginRight: flyoutWidth ? `${flyoutWidth + 12}px` : "0",
              marginLeft: sidebarWidth ? `${sidebarWidth + 12}px` : "0",
              width: `calc(100% - ${flyoutWidth + sidebarWidth}px)`,
            }}
          >
            <div className="toolbar">
              <div className="ai-status">
                <span className="ai-chip">
                  <span role="img" aria-label="ai">
                    AI
                  </span>
                  AI model
                </span>
                <span className="muted">{planning.modelVersion || "priority_model_v1"}</span>
                {planning.modelConfidence !== null && (
                  <span className="muted">Confidence: {(planning.modelConfidence * 100).toFixed(0)}%</span>
                )}
                <span className="ai-chip secondary">Learns from your feedback</span>
              </div>
              <div className="muted">Plan date</div>
              <input
                type="date"
                value={planning.planDate}
                onChange={(e) => planning.setPlanDate(e.target.value)}
                className="date-input"
              />
              <button
                className={pendingCount > 0 ? "" : "idle"}
                onClick={planning.generatePlan}
                disabled={planning.planning || pendingCount === 0}
              >
                {planning.planning ? "Thinking..." : "Ask AI to plan"}
              </button>
            </div>

            {tasks.length === 0 && (
              <div className="onboarding">
                <div className="onboarding-step">
                  <span className="ai-chip">1</span>
                  <div>Add a few tasks with deadlines, importance, and energy.</div>
                </div>
                <div className="onboarding-step">
                  <span className="ai-chip">2</span>
                  <div>Click "Ask AI to plan" to generate your day.</div>
                </div>
                <div className="onboarding-step">
                  <span className="ai-chip">3</span>
                  <div>Give feedback (earlier/later) to train the model.</div>
                </div>
              </div>
            )}

            <div className="schedule-wrap">
              <ScheduleView
                planDate={planning.planDate}
                calendarDays={planning.calendarDays}
                schedule={planning.schedule}
                unscheduled={planning.unscheduled}
                onFeedback={planning.sendFeedback}
                onReschedule={planning.rescheduleItem}
                onDeleteItem={planning.deletePlanEntry}
              />
              {planning.schedule.length > 0 && (
                <div className="ai-hint">
                  <span className="ai-chip secondary">AI in action</span>
                  <p className="muted">
                    Review the AI reasoning for each block. Your earlier/later feedback trains the planner for future days.
                  </p>
                </div>
              )}
              <div className="backlog-summary">
                <div className="inline">
                  <span className="ai-chip secondary">Backlog</span>
                  <span className="muted">
                    {tasks.length} tasks | {tasks.filter((t) => t.importance === "high").length} high /{" "}
                    {tasks.filter((t) => t.importance === "medium").length} med /{" "}
                    {tasks.filter((t) => t.importance === "low").length} low
                  </span>
                  <button className="ghost" onClick={() => setShowTasksPanel(true)}>
                    Open backlog &gt;
                  </button>
                </div>
              </div>

              <div className="calendar-board card">
                <div className="card-header">
                  <div>
                    <p className="eyebrow">Calendar</p>
                    <h4>Planned days this month</h4>
                  </div>
                </div>
                {planning.calendarDays.length === 0 && <p className="muted">No plans saved for this month yet.</p>}
                <div className="calendar-grid">
                  {planning.calendarDays.map((day) => (
                    <div key={day.plan_date} className="calendar-day" onClick={() => planning.setPlanDate(day.plan_date)}>
                      <div className="calendar-date">{new Date(day.plan_date).getDate()}</div>
                      <div className="calendar-items">
                        {day.scheduled.slice(0, 3).map((it) => (
                          <div key={it.task_id} className="calendar-item">
                            <div className="mini">
                              {new Date(it.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </div>
                            <div className="mini strong">{it.title}</div>
                          </div>
                        ))}
                        {day.scheduled.length === 0 && <div className="muted mini">No items</div>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </main>

          <div className="flyouts">
            {showInputPanel && (
              <div className="flyout">
                <div className="flyout-header">
                  <h4>
                    Input layer <span className="ai-chip secondary">AI uses this</span>
                  </h4>
                  <button className="icon-btn" onClick={() => setShowInputPanel(false)}>
                    x
                  </button>
                </div>
                <TaskForm onCreate={handleTaskCreate} loading={tasksLoading} />
              </div>
            )}

            {showTasksPanel && (
              <div className="flyout">
                <div className="flyout-header">
                  <h4>
                    Backlog overview <span className="ai-chip secondary">Feeds prioritization</span>
                  </h4>
                  <button className="icon-btn" onClick={() => setShowTasksPanel(false)}>
                    x
                  </button>
                </div>
                <TaskList tasks={tasks} />
              </div>
            )}

            {showUnscheduledPanel && (
              <div className="flyout">
                <div className="flyout-header">
                  <h4>Unscheduled</h4>
                  <button className="icon-btn" onClick={() => setShowUnscheduledPanel(false)}>
                    x
                  </button>
                </div>
                <div className="list">
                  {planning.unscheduled.length === 0 && <p className="muted">All tasks placed.</p>}
                  {planning.unscheduled.map((t) => (
                    <div key={t.id} className="list-item">
                      <div>
                        <strong>{t.title}</strong>
                        <p className="muted mini">Deadline {new Date(t.deadline).toLocaleString()}</p>
                        {t.reason && <p className="muted mini">Reason: {t.reason}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <NotesPanel
              isOpen={showNotesPanel}
              noteDraft={notes.noteDraft}
              notes={notes.notes}
              onDraftChange={notes.setNoteDraft}
              onAddNote={notes.handleAddNote}
              onClose={() => setShowNotesPanel(false)}
            />
          </div>
        </div>
      )}

      {toast.text && <div className={`toast ${toast.tone}`}>{toast.text}</div>}
    </div>
  );
};

export default App;
