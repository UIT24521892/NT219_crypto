import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const ROLE_LABEL = {
  admin: "Quản trị viên",
  reviewer: "Người duyệt",
  signer: "Người ký",
  citizen: "Công dân",
};

export default function Layout() {
  const { user, logout, role, isReviewer, isSigner } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  function isActive(path) {
    return location.pathname === path;
  }

  return (
    <div style={styles.wrapper}>
      <aside style={styles.sidebar}>
        <div style={styles.brand}>
          <div style={styles.emblem}>✓</div>
          <div>
            <h2 style={styles.brandTitle}>CDV Portal</h2>
            <p style={styles.brandSub}>Xác thực tài liệu số</p>
          </div>
        </div>

        <div style={styles.userCard}>
          <p style={styles.userLabel}>Tài khoản</p>
          <p style={styles.userEmail}>{user?.email || "user@example.com"}</p>
          <span style={styles.roleBadge}>{ROLE_LABEL[role] || "Công dân"}</span>
        </div>

        <nav style={styles.nav}>
          <Link
            style={{
              ...styles.navItem,
              ...(isActive("/documents") ? styles.navItemActive : {}),
            }}
            to="/documents"
          >
            <span>📄</span>
            <span>Quản lý tài liệu</span>
          </Link>

          {isReviewer && (
            <Link
              style={{
                ...styles.navItem,
                ...(isActive("/review") ? styles.navItemActive : {}),
              }}
              to="/review"
            >
              <span>🛡️</span>
              <span>Hàng chờ duyệt</span>
            </Link>
          )}

          {isSigner && (
            <Link
              style={{
                ...styles.navItem,
                ...(isActive("/sign") ? styles.navItemActive : {}),
              }}
              to="/sign"
            >
              <span>✍️</span>
              <span>Hàng chờ ký</span>
            </Link>
          )}

          <Link style={styles.navItem} to="/verify">
            <span>🔎</span>
            <span>Xác thực QR</span>
          </Link>
        </nav>

        <button style={styles.logout} onClick={handleLogout}>
          Đăng xuất
        </button>
      </aside>

      <main style={styles.main}>
        <header style={styles.topbar}>
          <div>
            <p style={styles.topbarLabel}>Hệ thống xác thực tài liệu hậu lượng tử</p>
            <h1 style={styles.topbarTitle}>Citizen Document Verification</h1>
          </div>

          <div style={styles.statusPill}>
            <span style={styles.dot}></span>
            Backend connected
          </div>
        </header>

        <section style={styles.content}>
          <Outlet />
        </section>
      </main>
    </div>
  );
}

const styles = {
  wrapper: {
    minHeight: "100vh",
    display: "flex",
    background: "#f3f5f8",
    color: "#172033",
  },
  sidebar: {
    width: 280,
    background: "linear-gradient(180deg, #8b1e1e 0%, #5c1111 100%)",
    color: "white",
    padding: 22,
    display: "flex",
    flexDirection: "column",
    gap: 20,
    boxShadow: "8px 0 30px rgba(15, 23, 42, 0.16)",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    paddingBottom: 14,
    borderBottom: "1px solid rgba(255,255,255,0.18)",
  },
  emblem: {
    width: 42,
    height: 42,
    borderRadius: 12,
    background: "#f8d477",
    color: "#7a1414",
    display: "grid",
    placeItems: "center",
    fontWeight: 900,
    fontSize: 22,
  },
  brandTitle: {
    margin: 0,
    fontSize: 21,
    letterSpacing: 0.2,
  },
  brandSub: {
    margin: "3px 0 0",
    color: "#f9d6d6",
    fontSize: 13,
  },
  userCard: {
    background: "rgba(255,255,255,0.1)",
    border: "1px solid rgba(255,255,255,0.16)",
    borderRadius: 14,
    padding: 14,
  },
  userLabel: {
    margin: 0,
    color: "#f4caca",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 0.6,
  },
  userEmail: {
    margin: "6px 0 10px",
    wordBreak: "break-all",
    fontSize: 14,
    fontWeight: 600,
  },
  roleBadge: {
    display: "inline-block",
    background: "#f8d477",
    color: "#6b1111",
    padding: "5px 9px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 800,
  },
  nav: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  navItem: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    color: "white",
    textDecoration: "none",
    padding: "12px 14px",
    borderRadius: 12,
    background: "rgba(255,255,255,0.08)",
    border: "1px solid rgba(255,255,255,0.1)",
    fontWeight: 650,
  },
  navItemActive: {
    background: "#f8d477",
    color: "#5c1111",
  },
  logout: {
    marginTop: "auto",
    border: 0,
    background: "#ffffff",
    color: "#8b1e1e",
    padding: "12px 14px",
    borderRadius: 12,
    fontWeight: 800,
    cursor: "pointer",
  },
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
  },
  topbar: {
    background: "white",
    borderBottom: "1px solid #e3e8ef",
    padding: "18px 28px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  topbarLabel: {
    margin: 0,
    color: "#7a1414",
    fontSize: 13,
    fontWeight: 800,
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  topbarTitle: {
    margin: "4px 0 0",
    fontSize: 24,
    color: "#111827",
  },
  statusPill: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    background: "#ecfdf5",
    color: "#047857",
    padding: "8px 12px",
    borderRadius: 999,
    fontSize: 13,
    fontWeight: 700,
  },
  dot: {
    width: 8,
    height: 8,
    background: "#10b981",
    borderRadius: "50%",
  },
  content: {
    padding: 28,
  },
};