import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function ProtectedRoute({ allow = null }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div style={{ padding: 40 }}>Đang kiểm tra đăng nhập...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  // `allow` is a list of roles permitted on this route; admin always passes.
  if (allow && user.role !== "admin" && !allow.includes(user.role)) {
    return <Navigate to="/documents" replace />;
  }

  return <Outlet />;
}