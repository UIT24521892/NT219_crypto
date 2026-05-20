import api from "./api";
import {
  mockGetDocuments,
  mockUploadDocument,
  mockSignDocument,
  mockGetDownloadUrl,
} from "./mockDb";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

export const getDocumentsApi = async () => {
  if (USE_MOCK) return mockGetDocuments();
  const res = await api.get("/documents");
  return res.data;
};

export const uploadDocumentApi = async (file) => {
  if (USE_MOCK) return mockUploadDocument(file);

  const formData = new FormData();
  formData.append("file", file);

  const res = await api.post("/documents/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return res.data;
};

export const signDocumentApi = async (id, payload) => {
  if (USE_MOCK) return mockSignDocument(id, payload);
  const res = await api.post(`/documents/${id}/sign`, payload);
  return res.data;
};

export const getDownloadUrl = (id) => {
  if (USE_MOCK) return mockGetDownloadUrl(id);
  return `http://localhost:5000/api/documents/${id}/download`;
};
