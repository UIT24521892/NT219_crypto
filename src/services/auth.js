import api from "./api";

export async function registerApi({ email, password, fullName }) {
  const res = await api.post("/auth/register", {
    email,
    password,
    full_name: fullName,
  });

  return res.data;
}

export async function loginApi({ email, password }) {
  const res = await api.post("/auth/login", {
    email,
    password,
  });

  return res.data;
}

export async function getMeApi() {
  const res = await api.get("/auth/me");
  return res.data;
}

export async function logoutApi() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
}