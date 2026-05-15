import { Link, useLocation, useNavigate } from "react-router-dom";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const userRaw = localStorage.getItem("user");
  const user = userRaw ? JSON.parse(userRaw) : null;

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("user");
    navigate("/login");
  };

  return (
    <header className="topbar shell">
      <div className="brand-wrap">
        <div className="brand-mark">CP</div>
        <div>
          <div className="brand-title">Cổng thông tin công dân</div>
          <div className="brand-subtitle">Quản lý hồ sơ số đơn giản và nhanh</div>
        </div>
      </div>

      <div className="topbar-actions">
        {user?.role === "citizen" && (
          <Link className={`nav-chip ${location.pathname === "/citizen" ? "active" : ""}`} to="/citizen">
            Công dân
          </Link>
        )}
        {user?.role === "admin" && (
          <Link className={`nav-chip ${location.pathname === "/admin" ? "active" : ""}`} to="/admin">
            Quản trị
          </Link>
        )}
        <div className="user-badge">{user?.fullName || user?.email || "Người dùng"}</div>
        <button className="btn btn-secondary" onClick={handleLogout}>Đăng xuất</button>
      </div>
    </header>
  );
}
