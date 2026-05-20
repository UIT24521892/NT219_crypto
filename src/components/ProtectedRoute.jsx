import { Navigate } from "react-router-dom";

export default function ProtectedRoute({ children, allowRole }) {
  const token = localStorage.getItem("accessToken");
  const userRaw = localStorage.getItem("user");

  if (!token || !userRaw) {
    return <Navigate to="/login" replace />;
  }

  const user = JSON.parse(userRaw);

  if (allowRole && user.role !== allowRole) {
    return <Navigate to="/login" replace />;
  }

  return children;
}