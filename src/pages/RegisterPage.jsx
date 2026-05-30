import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { registerApi } from "../services/auth";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleChange(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      await registerApi(form);
      navigate("/login", { replace: true });
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Đăng ký thất bại. Kiểm tra thông tin và thử lại."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main style={styles.page}>
      <form onSubmit={handleSubmit} style={styles.card}>
        <p style={styles.kicker}>Citizen Services Portal</p>
        <h1 style={styles.title}>Đăng ký tài khoản</h1>
        <p style={styles.subtitle}>Tạo tài khoản công dân để upload hồ sơ PDF.</p>

        <label style={styles.label}>
          Email
          <input
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
            required
            autoComplete="email"
            style={styles.input}
          />
        </label>

        <label style={styles.label}>
          Mật khẩu
          <input
            type="password"
            name="password"
            value={form.password}
            onChange={handleChange}
            required
            minLength={8}
            autoComplete="new-password"
            style={styles.input}
          />
        </label>

        {error && <div style={styles.error}>{error}</div>}

        <button type="submit" disabled={submitting} style={styles.button}>
          {submitting ? "Đang đăng ký..." : "Đăng ký"}
        </button>

        <p style={styles.helper}>
          Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
        </p>
      </form>
    </main>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    padding: 24,
    background: "#f3f5f8",
  },
  card: {
    width: "100%",
    maxWidth: 430,
    display: "flex",
    flexDirection: "column",
    gap: 14,
    padding: 32,
    background: "white",
    border: "1px solid #e5e7eb",
    borderRadius: 18,
    boxShadow: "0 18px 50px rgba(15,23,42,0.12)",
  },
  kicker: {
    margin: 0,
    color: "#8b1e1e",
    fontSize: 12,
    fontWeight: 900,
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  title: { margin: 0, color: "#111827" },
  subtitle: { margin: 0, color: "#64748b" },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: 7,
    color: "#334155",
    fontWeight: 800,
  },
  input: {
    padding: 11,
    border: "1px solid #cbd5e1",
    borderRadius: 10,
    fontSize: 15,
  },
  button: {
    padding: 12,
    border: 0,
    borderRadius: 10,
    background: "#8b1e1e",
    color: "white",
    fontWeight: 900,
    cursor: "pointer",
  },
  error: {
    padding: 11,
    borderRadius: 10,
    background: "#fef2f2",
    color: "#991b1b",
  },
  helper: { margin: 0, color: "#64748b" },
};
