import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const TEST_USERS = [
  {
    label: "Công dân Alice",
    email: "alice@example.com",
    password: "SecurePass123",
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

  function fillUser(user) {
    setEmail(user.email);
    setPassword(user.password);
    setError("");
  }

  return (
    <div style={styles.page}>
      <div style={styles.leftPanel}>
        <div style={styles.logoBox}>✓</div>
        <h1 style={styles.heroTitle}>Cổng xác thực tài liệu số</h1>
        <p style={styles.heroText}>
          Hệ thống hỗ trợ ký số tài liệu PDF bằng ML-DSA-44, tạo QR và xác thực
          công khai bằng công nghệ mật mã hậu lượng tử.
        </p>

        <div style={styles.featureList}>
          <div style={styles.feature}>SHA-256 File Hashing</div>
          <div style={styles.feature}>ML-DSA-44 Post-Quantum Signature</div>
          <div style={styles.feature}>Ed25519 Offline QR Verification</div>
        </div>
      </div>

      <div style={styles.rightPanel}>
        <form onSubmit={handleSubmit} style={styles.card}>
          <div style={styles.cardHeader}>
            <p style={styles.systemLabel}>NT219 Crypto Project</p>
            <h2 style={styles.title}>Đăng nhập</h2>
            <p style={styles.subtitle}>Truy cập hệ thống xác thực tài liệu</p>
          </div>

          <div style={styles.testBox}>
            <p style={styles.testTitle}>Tài khoản kiểm thử</p>

            <div style={styles.testButtons}>
              {TEST_USERS.map((user) => (
                <button
                  key={user.email}
                  type="button"
                  onClick={() => fillUser(user)}
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
            {submitting ? "Đang xác thực..." : "Đăng nhập"}
          </button>

          <p style={styles.helper}>
            Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    display: "grid",
    gridTemplateColumns: "1.05fr 0.95fr",
    background: "#f3f5f8",
  },
  leftPanel: {
    background: "linear-gradient(135deg, #8b1e1e 0%, #4d0f0f 100%)",
    color: "white",
    padding: "70px 70px",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
  },
  logoBox: {
    width: 64,
    height: 64,
    borderRadius: 18,
    background: "#f8d477",
    color: "#711515",
    display: "grid",
    placeItems: "center",
    fontSize: 32,
    fontWeight: 900,
    marginBottom: 24,
  },
  heroTitle: {
    fontSize: 42,
    lineHeight: 1.15,
    margin: 0,
  },
  heroText: {
    fontSize: 16,
    lineHeight: 1.7,
    color: "#fde8e8",
    maxWidth: 620,
    marginTop: 18,
  },
  featureList: {
    display: "flex",
    flexWrap: "wrap",
    gap: 10,
    marginTop: 26,
  },
  feature: {
    background: "rgba(255,255,255,0.12)",
    border: "1px solid rgba(255,255,255,0.16)",
    borderRadius: 999,
    padding: "9px 13px",
    fontWeight: 700,
    fontSize: 13,
  },
  rightPanel: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
  },
  card: {
    width: "100%",
    maxWidth: 430,
    background: "white",
    padding: 32,
    borderRadius: 18,
    boxShadow: "0 18px 50px rgba(15,23,42,0.12)",
    border: "1px solid #e5e7eb",
    display: "flex",
    flexDirection: "column",
    gap: 14,
  },
  cardHeader: {
    marginBottom: 4,
  },
  systemLabel: {
    margin: 0,
    color: "#8b1e1e",
    fontWeight: 800,
    fontSize: 12,
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  title: {
    margin: "5px 0 0",
    fontSize: 27,
    color: "#111827",
  },
  subtitle: {
    margin: "6px 0 0",
    color: "#6b7280",
    fontSize: 14,
  },
  testBox: {
    background: "#fff7ed",
    border: "1px solid #fed7aa",
    borderRadius: 12,
    padding: 12,
  },
  testTitle: {
    margin: "0 0 8px",
    color: "#9a3412",
    fontSize: 13,
    fontWeight: 800,
  },
  testButtons: {
    display: "flex",
    gap: 8,
    flexWrap: "wrap",
  },
  btnGhost: {
    border: "1px solid #d9b36d",
    background: "white",
    color: "#7a1414",
    padding: "7px 10px",
    borderRadius: 8,
    cursor: "pointer",
    fontWeight: 700,
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    fontWeight: 700,
    color: "#374151",
  },
  input: {
    padding: "12px 13px",
    border: "1px solid #cbd5e1",
    borderRadius: 10,
    fontSize: 15,
    outlineColor: "#8b1e1e",
  },
  btnPrimary: {
    background: "linear-gradient(135deg, #9f1d20, #7a1414)",
    color: "white",
    border: 0,
    padding: "13px 16px",
    borderRadius: 10,
    fontWeight: 800,
    cursor: "pointer",
    fontSize: 15,
    boxShadow: "0 8px 20px rgba(139,30,30,0.25)",
  },
  error: {
    background: "#fee2e2",
    color: "#991b1b",
    padding: "10px 12px",
    borderRadius: 10,
    fontSize: 14,
  },
  helper: {
    textAlign: "center",
    color: "#6b7280",
    fontSize: 14,
    margin: 0,
  },
};