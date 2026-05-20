import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const TEST_USERS = [
  {
    label: "Citizen Alice",
    email: "alice@example.com",
    password: "SecurePass123",
  },
  {
    label: "Citizen Bob",
    email: "bob@example.com",
    password: "BobPass123",
  },
  {
    label: "Admin",
    email: "admin@example.com",
    password: "AdminPass123",
  },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const redirectTo = location.state?.from?.pathname || "/documents";

  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("AdminPass123");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setSubmitting(true);

    try {
      await login(email.trim(), password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Đăng nhập thất bại. Kiểm tra backend hoặc tài khoản."
      );
    } finally {
      setSubmitting(false);
    }
  }

  function fillTestUser(user) {
    setEmail(user.email);
    setPassword(user.password);
    setError("");
  }

  return (
    <div style={styles.wrapper}>
      <form onSubmit={handleSubmit} style={styles.card}>
        <h1 style={styles.title}>Đăng nhập</h1>
        <p style={styles.subtitle}>Citizen Document Verification Portal</p>

        <div style={styles.testBox}>
          <p style={styles.testTitle}>Tài khoản test</p>

          <div style={styles.testButtons}>
            {TEST_USERS.map((user) => (
              <button
                key={user.email}
                type="button"
                onClick={() => fillTestUser(user)}
                style={styles.btnGhost}
              >
                {user.label}
              </button>
            ))}
          </div>
        </div>

        <label style={styles.label}>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            style={styles.input}
          />
        </label>

        <label style={styles.label}>
          Mật khẩu
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            style={styles.input}
          />
        </label>

        {error && <div style={styles.error}>{error}</div>}

        <button
          type="submit"
          disabled={submitting || !email || !password}
          style={{
            ...styles.btnPrimary,
            opacity: submitting || !email || !password ? 0.7 : 1,
          }}
        >
          {submitting ? "Đang đăng nhập..." : "Đăng nhập"}
        </button>

        <p style={styles.helper}>
          Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
        </p>
      </form>
    </div>
  );
}

const styles = {
  wrapper: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#f5f7fb",
    padding: 24,
  },
  card: {
    width: "100%",
    maxWidth: 430,
    background: "white",
    padding: 32,
    borderRadius: 12,
    boxShadow: "0 8px 30px rgba(15,23,42,0.08)",
    display: "flex",
    flexDirection: "column",
    gap: 14,
  },
  title: {
    margin: 0,
    fontSize: 24,
    color: "#1e3a8a",
  },
  subtitle: {
    margin: 0,
    color: "#6b7280",
    fontSize: 14,
  },
  testBox: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: 12,
  },
  testTitle: {
    margin: "0 0 8px",
    fontSize: 13,
    color: "#475569",
    fontWeight: 600,
  },
  testButtons: {
    display: "flex",
    gap: 8,
    flexWrap: "wrap",
  },
  btnGhost: {
    border: "1px solid #cbd5e1",
    background: "white",
    color: "#1e3a8a",
    padding: "6px 10px",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 13,
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
    fontWeight: 500,
  },
  input: {
    padding: "10px 12px",
    border: "1px solid #cbd5e1",
    borderRadius: 6,
    fontSize: 14,
  },
  btnPrimary: {
    background: "#1e3a8a",
    color: "white",
    border: 0,
    padding: "12px 16px",
    borderRadius: 6,
    fontWeight: 600,
    cursor: "pointer",
    fontSize: 15,
  },
  error: {
    background: "#fee2e2",
    color: "#991b1b",
    padding: "8px 12px",
    borderRadius: 6,
    fontSize: 14,
  },
  helper: {
    textAlign: "center",
    color: "#6b7280",
    fontSize: 14,
    margin: 0,
  },
};