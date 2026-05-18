import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function Layout() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div style={styles.wrapper}>
      <aside style={styles.sidebar}>
        <h2 style={styles.logo}>NT219</h2>
        <p style={styles.user}>{user?.email}</p>

        <nav style={styles.nav}>
          <Link style={styles.link} to="/documents">
            Tài liệu
          </Link>

          {isAdmin && (
            <Link style={styles.link} to="/admin">
              Admin
            </Link>
          )}

          <Link style={styles.link} to="/verify">
            Verify QR
          </Link>

          <button style={styles.logout} onClick={handleLogout}>
            Đăng xuất
          </button>
        </nav>
      </aside>

      <main style={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}

const styles = {
  wrapper: {
    minHeight: "100vh",
    display: "flex",
    background: "#f8fafc",
  },
  sidebar: {
    width: 240,
    background: "#0f172a",
    color: "white",
    padding: 20,
  },
  logo: {
    margin: "0 0 12px",
  },
  user: {
    fontSize: 13,
    color: "#cbd5e1",
    wordBreak: "break-all",
  },
  nav: {
    marginTop: 24,
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  link: {
    color: "white",
    textDecoration: "none",
    background: "#1e293b",
    padding: "10px 12px",
    borderRadius: 8,
  },
  logout: {
    marginTop: 16,
    background: "#dc2626",
    color: "white",
    border: 0,
    padding: "10px 12px",
    borderRadius: 8,
    cursor: "pointer",
  },
  main: {
    flex: 1,
    padding: 24,
  },
};