import React, { useState } from "react";

const TaskForm = ({ onCreate, loading }) => {
  const [title, setTitle] = useState("");
  const [duration, setDuration] = useState(60);
  const [deadline, setDeadline] = useState("");
  const [taskType, setTaskType] = useState("study");
  const [importance, setImportance] = useState("medium");
  const [prefTime, setPrefTime] = useState("anytime");
  const [energy, setEnergy] = useState("medium");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!deadline) return;
    await onCreate({
      title,
      duration_minutes: Number(duration),
      deadline: new Date(deadline).toISOString(),
      task_type: taskType,
      importance,
      preferred_time: prefTime,
      energy,
    });
    setTitle("");
  };

  return (
    <form className="card" onSubmit={handleSubmit}>
      <div className="card-header">
        <div>
          <p className="eyebrow">Input layer</p>
          <h3>Add task</h3>
        </div>
        <div className="pill">Feature-rich</div>
      </div>
      <div className="form-grid">
        <label>
          <span>Title</span>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <label>
          <span>Duration (min)</span>
          <input
            type="number"
            min={15}
            step={15}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
        </label>
        <label>
          <span>Deadline</span>
          <input
            type="datetime-local"
            required
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
          />
        </label>
        <label>
          <span>Task type</span>
          <select value={taskType} onChange={(e) => setTaskType(e.target.value)}>
            <option value="study">Study</option>
            <option value="work">Work</option>
            <option value="meeting">Meeting</option>
            <option value="personal">Personal</option>
            <option value="social">Social</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <label>
          <span>Importance</span>
          <select value={importance} onChange={(e) => setImportance(e.target.value)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
        <label>
          <span>Preferred time</span>
          <select value={prefTime} onChange={(e) => setPrefTime(e.target.value)}>
            <option value="morning">Morning</option>
            <option value="afternoon">Afternoon</option>
            <option value="evening">Evening</option>
            <option value="anytime">Anytime</option>
          </select>
        </label>
        <label>
          <span>Energy</span>
          <select value={energy} onChange={(e) => setEnergy(e.target.value)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
      </div>
      <button type="submit" disabled={loading}>
        {loading ? "Saving..." : "Add task"}
      </button>
    </form>
  );
};

export default TaskForm;
