import React, { useState, useEffect, useMemo } from "react";
import LoginForm from "./components/LoginForm";
import TaskForm from "./components/TaskForm";
import TaskList from "./components/TaskList";
import ScheduleView from "./components/ScheduleView";
import {
  login,
  signupOrLogin,
  createTask,
  getTasks,
  generatePlan,
  getPlan,
  getCalendarRange,
  updatePlanItem,
  deletePlanItem,
  setAuthToken,
  logFeedback,
  refreshAccessToken,
  getNotes,
  addNote,
} from "./api";

const App = () => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [planDate, setPlanDate] = useState(new Date().toISOString().substring(0, 10));
  const [schedule, setSchedule] = useState([]);
  const [unscheduled, setUnscheduled] = useState([]);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState({ text: "", tone: "info" });
  const [modelVersion, setModelVersion] = useState("");
  const [modelConfidence, setModelConfidence] = useState(null);

  const [showInputPanel, setShowInputPanel] = useState(false);
  const [showTasksPanel, setShowTasksPanel] = useState(false);
  const [showUnscheduledPanel, setShowUnscheduledPanel] = useState(false);
  const [showNotesPanel, setShowNotesPanel] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);
  const [notes, setNotes] = useState([]);
  const [noteDraft, setNoteDraft] = useState({ title: "", body: "" });
  const showToast = (text, tone = "info") => setToast({ text, tone });
  const [calendarDays, setCalendarDays] = useState([]);

  const anyFlyoutOpen = useMemo(
    () => showInputPanel || showTasksPanel || showUnscheduledPanel || showNotesPanel,
    [showInputPanel, showTasksPanel, showUnscheduledPanel, showNotesPanel]
  );

  const flyoutWidth = anyFlyoutOpen ? 380 : 0;
  const sidebarWidth = showSidebar ? 240 : 0;

  const handleAuth = async ({ email, name, profile, password, mode }) => {
    setLoading(true);
    try {
      const res =
        mode === "login"
          ? await login({ email, password })
          : await signupOrLogin({ email, name, profile, password });
      setAuthToken(res.access_token);
      setToken(res.access_token);
      setUser(res.user);
      showToast(mode === "login" ? "Logged in." : "Welcome to OptimaTime AI.", "success");
    } catch (err) {
      console.error("Auth failed", err);
      showToast(
        err?.response?.data?.detail || err?.message || "Unable to sign up/login. Please try again.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  const withRefresh = async (fn) => {
    try {
      return await fn();
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        try {
          const refreshed = await refreshAccessToken();
          setAuthToken(refreshed.access_token);
          setUser(refreshed.user);
          return await fn();
        } catch (err2) {
          console.error("Refresh failed", err2);
          setAuthToken(null);
          setUser(null);
          setTasks([]);
          setSchedule([]);
          setUnscheduled([]);
          showToast("Session expired. Please log in again.", "error");
          throw err2;
        }
      }
      throw err;
    }
  };

  const refreshTasks = async () => {
    if (!user) return;
    try {
      const data = await withRefresh(() => getTasks());
      setTasks(data);
    } catch (err) {
      console.error("Failed to load tasks", err);
      showToast("Cannot reach API. Is the backend running?", "error");
    }
  };

  const refreshNotes = async () => {
    if (!user) return;
    try {
      const data = await withRefresh(() => getNotes());
      setNotes(data);
    } catch (err) {
      console.error("Failed to load notes", err);
    }
  };

  const handleLogout = () => {
    setAuthToken(null);
    setToken(null);
    setUser(null);
    setTasks([]);
    setSchedule([]);
    setUnscheduled([]);
    setNotes([]);
    showToast("Signed out.", "info");
  };

  useEffect(() => {
    if (user) {
      refreshTasks();
      refreshPlanAndCalendar();
    }
  }, [user]);

  useEffect(() => {
    if (user && showNotesPanel) {
      refreshNotes();
    }
  }, [user, showNotesPanel]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  useEffect(() => {
    refreshPlanAndCalendar();
  }, [planDate, user]);

  const handleTaskCreate = async (task) => {
    if (!user) return;
    setLoading(true);
    try {
      await withRefresh(() => createTask(task));
      await refreshTasks();
      showToast("Task added and ready for prioritization.", "success");
    } catch (err) {
      console.error("Task add failed", err);
      showToast("Could not add task. Please try again.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePlan = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const data = await withRefresh(() => generatePlan(planDate));
      setModelVersion(data.model_version || "");
      setModelConfidence(data.model_confidence ?? null);
      setSchedule(data.scheduled || []);
      setUnscheduled(data.unscheduled || []);
      await refreshTasks();
      showToast("AI planner generated your day.", "success");
    } catch (err) {
      console.error("Plan failed", err);
      showToast(err?.response?.data?.detail || "Unable to generate plan.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleReschedule = async (planItemId, start, end) => {
    if (!planItemId) return;
    try {
      await withRefresh(() => updatePlanItem(planItemId, start, end));
      await refreshPlanAndCalendar();
      showToast("Updated schedule.", "success");
    } catch (err) {
      console.error("Reschedule failed", err);
      showToast("Could not update this item.", "error");
    }
  };

  const handleDeletePlanItem = async (planItemId) => {
    if (!planItemId) return;
    try {
      await withRefresh(() => deletePlanItem(planItemId));
      await refreshPlanAndCalendar();
      showToast("Removed from calendar.", "success");
    } catch (err) {
      console.error("Delete plan item failed", err);
      showToast("Could not remove this item.", "error");
    }
  };

  const refreshPlanAndCalendar = async () => {
    if (!user) return;
    try {
      const data = await withRefresh(() => getPlan(planDate));
      setModelVersion(data.model_version || "");
      setModelConfidence(data.model_confidence ?? null);
      setSchedule(data.scheduled || []);
      setUnscheduled(data.unscheduled || []);
    } catch (err) {
      if (err?.response?.status === 404) {
        setSchedule([]);
        setUnscheduled([]);
      }
    }
    const d = new Date(planDate);
    const start = new Date(d.getFullYear(), d.getMonth(), 1).toISOString().substring(0, 10);
    const end = new Date(d.getFullYear(), d.getMonth() + 1, 0).toISOString().substring(0, 10);
    try {
      const res = await withRefresh(() => getCalendarRange(start, end));
      setCalendarDays(res.days || []);
    } catch {
      setCalendarDays([]);
    }
  };

  const handleFeedback = async ({ taskId, outcome }) => {
    if (!user) return;
    try {
      await withRefresh(() => logFeedback({ taskId, outcome }));
      showToast("Feedback captured - the planner will adapt.", "success");
    } catch (err) {
      console.error("Feedback failed", err);
      showToast("Could not send feedback. Is the backend reachable?", "error");
    }
  };

  const handleAddNote = async () => {
    if (!noteDraft.title) return;
    try {
      await withRefresh(() => addNote(noteDraft));
      setNoteDraft({ title: "", body: "" });
      await refreshNotes();
    } catch (err) {
      console.error("Add note failed", err);
    }
  };

  const initials = user?.name ? user.name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase() : "";
  const pendingCount = useMemo(
    () => tasks.filter((t) => t.status === "pending" || t.status === "unscheduled").length,
    [tasks]
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="top-left">
          {user && (
            <button className="hamburger" onClick={() => setShowSidebar((v) => !v)}>
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
            <button className="ghost" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        )}
      </header>

      {!user && (
        <section className="auth-wrapper">
          <LoginForm onLoggedIn={handleAuth} loading={loading} />
        </section>
      )}

      {user && (
        <div className={`app-layout ${anyFlyoutOpen ? "flyouts-open" : ""}`}>
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
              <button
                className={showInputPanel ? "sidebar-btn active" : "sidebar-btn"}
                onClick={() => setShowInputPanel((v) => !v)}
              >
                Input Layer
              </button>
              <button
                className={showTasksPanel ? "sidebar-btn active" : "sidebar-btn"}
                onClick={() => setShowTasksPanel((v) => !v)}
              >
                Backlog Overview
              </button>
              <button
                className={showUnscheduledPanel ? "sidebar-btn active" : "sidebar-btn"}
                onClick={() => setShowUnscheduledPanel((v) => !v)}
              >
                Unscheduled
              </button>
              <button
                className={showNotesPanel ? "sidebar-btn active" : "sidebar-btn"}
                onClick={() => setShowNotesPanel((v) => !v)}
              >
                Notes
              </button>
              <button
                className={darkMode ? "sidebar-btn active" : "sidebar-btn"}
                onClick={() => setDarkMode((d) => !d)}
              >
                {darkMode ? "Light mode" : "Dark mode"}
              </button>
            </div>
          </aside>

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
                    🤖
                  </span>
                  AI model
                </span>
                <span className="muted">{modelVersion || "priority_model_v1"}</span>
                {modelConfidence !== null && (
                  <span className="muted">Confidence: {(modelConfidence * 100).toFixed(0)}%</span>
                )}
                <span className="ai-chip secondary">Learns from your feedback</span>
              </div>
              <div className="muted">Plan date</div>
              <input
                type="date"
                value={planDate}
                onChange={(e) => setPlanDate(e.target.value)}
                className="date-input"
              />
              <button
                className={pendingCount > 0 ? "" : "idle"}
                onClick={handleGeneratePlan}
                disabled={loading || pendingCount === 0}
              >
                {loading ? "Thinking..." : "Ask AI to plan"}
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
                  <div>Click “Ask AI to plan” to generate your day.</div>
                </div>
                <div className="onboarding-step">
                  <span className="ai-chip">3</span>
                  <div>Give feedback (earlier/later) to train the model.</div>
                </div>
              </div>
            )}

            <div className="schedule-wrap">
              <ScheduleView
                planDate={planDate}
                calendarDays={calendarDays}
                schedule={schedule}
                unscheduled={unscheduled}
                onFeedback={handleFeedback}
                onReschedule={handleReschedule}
                onDeleteItem={handleDeletePlanItem}
              />
              {schedule.length > 0 && (
                <div className="ai-hint">
                  <span className="ai-chip secondary">AI in action</span>
                  <p className="muted">
                    Review the AI reasoning for each block. Your “Prefer earlier/later” feedback trains the planner for
                    future days.
                  </p>
                </div>
              )}
              <div className="backlog-summary">
                <div className="inline">
                  <span className="ai-chip secondary">Backlog</span>
                  <span className="muted">
                    {tasks.length} tasks · {tasks.filter((t) => t.importance === "high").length} high /{" "}
                    {tasks.filter((t) => t.importance === "medium").length} med /{" "}
                    {tasks.filter((t) => t.importance === "low").length} low
                  </span>
                  <button className="ghost" onClick={() => setShowTasksPanel(true)}>
                    Open backlog ▸
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
                {calendarDays.length === 0 && <p className="muted">No plans saved for this month yet.</p>}
                <div className="calendar-grid">
                  {calendarDays.map((day) => (
                    <div key={day.plan_date} className="calendar-day" onClick={() => setPlanDate(day.plan_date)}>
                      <div className="calendar-date">{new Date(day.plan_date).getDate()}</div>
                      <div className="calendar-items">
                        {day.scheduled.slice(0, 3).map((it) => (
                          <div key={it.task_id} className="calendar-item">
                            <div className="mini">{new Date(it.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
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
                    ×
                  </button>
                </div>
                <TaskForm onCreate={handleTaskCreate} loading={loading} />
              </div>
            )}

            {showTasksPanel && (
              <div className="flyout">
                <div className="flyout-header">
                  <h4>
                    Backlog overview <span className="ai-chip secondary">Feeds prioritization</span>
                  </h4>
                  <button className="icon-btn" onClick={() => setShowTasksPanel(false)}>
                    ×
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
                    ×
                  </button>
                </div>
                <div className="list">
                  {unscheduled.length === 0 && <p className="muted">All tasks placed.</p>}
                  {unscheduled.map((t) => (
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

            {showNotesPanel && (
              <div className="flyout">
                <div className="flyout-header">
                  <h4>Notes</h4>
                  <button className="icon-btn" onClick={() => setShowNotesPanel(false)}>
                    ×
                  </button>
                </div>
                <div className="form-grid">
                  <label>
                    <span>Title</span>
                    <input
                      type="text"
                      value={noteDraft.title}
                      onChange={(e) => setNoteDraft({ ...noteDraft, title: e.target.value })}
                    />
                  </label>
                  <label>
                    <span>Body</span>
                    <textarea
                      rows={3}
                      value={noteDraft.body}
                      onChange={(e) => setNoteDraft({ ...noteDraft, body: e.target.value })}
                    />
                  </label>
                  <button onClick={handleAddNote} disabled={!noteDraft.title}>
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
            )}

          </div>
        </div>
      )}

      {toast.text && <div className={`toast ${toast.tone}`}>{toast.text}</div>}
    </div>
  );
};

export default App;
