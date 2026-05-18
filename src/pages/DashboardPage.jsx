import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <main style={{ padding: 24 }}>
      <h1>Citizen Document Verification Portal</h1>
      <p>Xin chào, {user?.fullName || user?.email || "User"}</p>

      <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
        <Link to="/documents">Quản lý tài liệu</Link>
        <Link to="/verify">Xác thực QR</Link>
        <button onClick={logout}>Đăng xuất</button>
      </div>
    </main>
  );
}