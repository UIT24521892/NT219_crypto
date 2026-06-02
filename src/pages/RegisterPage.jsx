import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerApi } from "../services/auth";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ fullName: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await registerApi(form);
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || "Đăng ký thất bại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={styles.page}>
      <form onSubmit={handleSubmit} style={styles.card}>
        <p style={styles.kicker}>Citizen Portal</p>
        <h1 style={styles.title}>Đăng ký tài khoản</h1>

        <label style={styles.label}>Họ tên
          <input name="fullName" value={form.fullName} onChange={handleChange} style={styles.input} />
        </label>

        <label style={styles.label}>Email
          <input name="email" type="email" required value={form.email} onChange={handleChange} style={styles.input} />
        </label>

        <label style={styles.label}>Mật khẩu
          <input name="password" type="password" required minLength={8} value={form.password} onChange={handleChange} style={styles.input} />
        </label>

        {error && <p style={styles.error}>{error}</p>}

        <button type="submit" disabled={loading} style={styles.button}>{loading ? "Đang đăng ký..." : "Đăng ký"}</button>
        <p style={styles.helper}>Đã có tài khoản? <Link to="/login">Đăng nhập</Link></p>
      </form>
    </main>
  );
}

const styles = {
  page: { minHeight: "100vh", display: "grid", placeItems: "center", background: "#f3f5f8", padding: 24 },
  card: { width: "100%", maxWidth: 430, background: "white", borderRadius: 18, padding: 30, border: "1px solid #e5e7eb", boxShadow: "0 18px 50px rgba(15,23,42,0.12)", display: "flex", flexDirection: "column", gap: 14 },
  kicker: { margin: 0, color: "#8b1e1e", fontWeight: 900, textTransform: "uppercase", fontSize: 12, letterSpacing: 0.8 },
  title: { margin: "4px 0 8px", color: "#111827" },
  label: { display: "flex", flexDirection: "column", gap: 6, color: "#374151", fontWeight: 800, fontSize: 13 },
  input: { padding: "11px 12px", borderRadius: 10, border: "1px solid #cbd5e1", fontSize: 14 },
  button: { background: "#8b1e1e", color: "white", border: 0, borderRadius: 10, padding: "12px 14px", fontWeight: 900, cursor: "pointer" },
  error: { margin: 0, background: "#fef2f2", color: "#b91c1c", border: "1px solid #fecaca", borderRadius: 10, padding: 10, fontWeight: 700 },
  helper: { textAlign: "center", color: "#64748b" },
};
