import api from "./api";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

export const verifyQrApi = async (payload) => {
  if (USE_MOCK) {
    return {
      valid: true,
      message: "Mock verify thành công",
      algorithm: payload.algorithm || "FALCON-512",
      documentHash: payload.documentHash,
      checkedAt: new Date().toISOString(),
    };
  }

  const res = await api.post("/verify", payload);
  return res.data;
};