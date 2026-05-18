import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function verifyDocument(docId) {
  const res = await axios.get(`${API_BASE}/verify`, {
    params: {
      d: docId,
    },
  });

  return res.data;
}