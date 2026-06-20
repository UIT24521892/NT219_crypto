import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./contexts/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";

import LoginPage from "./pages/LoginPage";
import VerifyPage from "./pages/VerifyPage";

import RegisterPage from "./pages/RegisterPage";
import DocumentsListPage from "./pages/DocumentsListPage";
import DocumentDetailPage from "./pages/DocumentDetailPage";
import ReviewerPage from "./pages/ReviewerPage";
import SignerPage from "./pages/SignerPage";
import AgenciesPage from "./pages/AgenciesPage";

function RootRedirect() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ padding: 40 }}>
        Đang tải...
      </div>
    );
  }

  return (
    <Navigate
      to={user ? "/documents" : "/login"}
      replace
    />
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>

          {/* Public routes */}
          <Route path="/" element={<RootRedirect />} />

          <Route
            path="/login"
            element={<LoginPage />}
          />

          <Route
            path="/register"
            element={<RegisterPage />}
          />

          <Route
            path="/verify"
            element={<VerifyPage />}
          />

          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>

              <Route
                path="/documents"
                element={<DocumentsListPage />}
              />

              <Route
                path="/documents/:id"
                element={<DocumentDetailPage />}
              />

            </Route>
          </Route>

          {/* Reviewer queue — approve/reject pending documents */}
          <Route element={<ProtectedRoute allow={["reviewer"]} />}>
            <Route element={<Layout />}>

              <Route
                path="/review"
                element={<ReviewerPage />}
              />

            </Route>
          </Route>

          {/* Signer queue — apply ML-DSA-44 signature to approved documents */}
          <Route element={<ProtectedRoute allow={["signer"]} />}>
            <Route element={<Layout />}>

              <Route
                path="/sign"
                element={<SignerPage />}
              />

            </Route>
          </Route>

          {/* Admin — manage government agencies + assign signers */}
          <Route element={<ProtectedRoute allow={["admin"]} />}>
            <Route element={<Layout />}>

              <Route
                path="/agencies"
                element={<AgenciesPage />}
              />

            </Route>
          </Route>

          {/* Fallback */}
          <Route
            path="*"
            element={<Navigate to="/" replace />}
          />

        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}