import api from "./api";
import { mockLogin, mockMe, mockRegister } from "./mockDb";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

export const registerApi = async (payload) => {
  if (USE_MOCK) return mockRegister(payload);
  const res = await api.post("/auth/register", payload);
  return res.data;
};

export const loginApi = async (payload) => {
  if (USE_MOCK) return mockLogin(payload);
  const res = await api.post("/auth/login", payload);
  return res.data;
};

export const meApi = async () => {
  if (USE_MOCK) return mockMe();
  const res = await api.get("/auth/me");
  return res.data;
};
