import React, { useState } from "react";

const LoginForm = ({ onLoggedIn, loading }) => {
  const [mode, setMode] = useState("signup"); // signup | login
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [profile, setProfile] = useState("student");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    await onLoggedIn({
      email,
      name,
      profile,
      password: password || undefined,
      mode,
    });
  };

  return (
    <form className="auth-card" onSubmit={handleSubmit}>
      <div className="auth-tabs">
        <button
          type="button"
          className={mode === "signup" ? "tab active" : "tab"}
          onClick={() => setMode("signup")}
        >
          Sign up
        </button>
        <button
          type="button"
          className={mode === "login" ? "tab active" : "tab"}
          onClick={() => setMode("login")}
        >
          Login
        </button>
      </div>

      <div className="auth-body">
        <h3>{mode === "signup" ? "Create your account" : "Welcome back"}</h3>
        <p className="muted">
          AI-powered planning that learns from your profile, tasks, and feedback.
        </p>

        <div className="form-grid">
          <label>
            <span>Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>

          {mode === "signup" && (
            <>
              <label>
                <span>Name</span>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
              <label>
                <span>Profile</span>
                <select value={profile} onChange={(e) => setProfile(e.target.value)}>
                  <option value="student">Student</option>
                  <option value="worker">Working Professional</option>
                  <option value="entrepreneur">Entrepreneur</option>
                </select>
              </label>
            </>
          )}

          <label>
            <span>Password</span>
            <input
              type="password"
              required={mode === "login"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === "signup" ? "Min 6 characters" : "Your password"}
            />
          </label>
        </div>

        <button type="submit" className="primary" disabled={loading}>
          {loading
            ? "Loading..."
            : mode === "signup"
            ? "Create & ask AI to plan"
            : "Login"}
        </button>
      </div>
    </form>
  );
};

export default LoginForm;
