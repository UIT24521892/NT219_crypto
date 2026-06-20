import { createContext, useContext, useEffect, useState } from "react";
import { getMeApi, loginApi, logoutApi } from "../services/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  async function loadCurrentUser() {
    const token = localStorage.getItem("access_token");

    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const me = await getMeApi();
      setUser(me);
    } catch {
      localStorage.removeItem("access_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Fetching the current session once on mount is intentional.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadCurrentUser();
  }, []);

  async function login(email, password) {
    const data = await loginApi({ email, password });
    localStorage.setItem("access_token", data.access_token);

    const me = await getMeApi();
    setUser(me);

    return me;
  }

  function logout() {
    logoutApi();
    setUser(null);
  }

  const role = user?.role || null;

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        role,
        agencyId: user?.agency_id ?? null,
        isAdmin: role === "admin",
        // Admin retains every staff capability (super-role).
        isReviewer: role === "reviewer" || role === "admin",
        isSigner: role === "signer" || role === "admin",
        isStaff: ["admin", "reviewer", "signer"].includes(role),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);

  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return ctx;
}
