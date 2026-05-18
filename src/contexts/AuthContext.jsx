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
      localStorage.setItem("user", JSON.stringify(me));
    } catch (err) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCurrentUser();
  }, []);

  async function login(email, password) {
    const data = await loginApi({ email, password });
    localStorage.setItem("access_token", data.access_token);

    const me = await getMeApi();
    setUser(me);
    localStorage.setItem("user", JSON.stringify(me));

    return me;
  }

  function logout() {
    logoutApi();
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        isAdmin: user?.role === "admin",
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);

  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return ctx;
}