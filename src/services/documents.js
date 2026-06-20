import api from "./api";

export async function listDocuments({ limit = 20, offset = 0 } = {}) {
  const res = await api.get("/documents", {
    params: { limit, offset },
  });

  return res.data;
}

export async function getDocument(id) {
  const res = await api.get(`/documents/${id}`);
  return res.data;
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await api.post("/documents/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return res.data;
}

export async function downloadDocument(id) {
  const res = await api.get(`/documents/${id}/download`, {
    responseType: "blob",
  });

  return res.data;
}

export async function signDocument(id) {
  const res = await api.post(`/documents/${id}/sign`);
  return res.data;
}

export async function approveDocument(id, note) {
  const res = await api.post(`/documents/${id}/approve`, { note: note || null });
  return res.data;
}

export async function rejectDocument(id, note) {
  const res = await api.post(`/documents/${id}/reject`, { note });
  return res.data;
}

export async function downloadSignedDocument(id) {
  const res = await api.get(`/documents/${id}/signed-download`, {
    responseType: "blob",
  });

  return res.data;
}

export async function getQrCode(id) {
  const res = await api.post(`/documents/${id}/qr`, null, {
    responseType: "blob",
  });

  return URL.createObjectURL(res.data);
}

export async function getVerificationPackage(id) {
  const res = await api.get(`/documents/${id}/verification-package`);
  return res.data;
}
