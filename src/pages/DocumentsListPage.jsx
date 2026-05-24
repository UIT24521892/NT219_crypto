import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import {
  listDocuments,
  uploadDocument,
  signDocument,
} from "../services/documents";

export default function DocumentsListPage() {
  const { isAdmin } = useAuth();

  const [documents, setDocuments] = useState([]);
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [signingId, setSigningId] = useState(null);

  async function loadDocuments() {
    setLoading(true);
    setMessage("");

    try {
      const data = await listDocuments();

      if (Array.isArray(data)) {
        setDocuments(data);
      } else if (Array.isArray(data.items)) {
        setDocuments(data.items);
      } else if (Array.isArray(data.documents)) {
        setDocuments(data.documents);
      } else {
        setDocuments([]);
      }
    } catch (err) {
      setMessage(
        err.response?.data?.detail ||
          "Chưa kết nối được backend hoặc API /documents lỗi."
      );
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  async function handleUpload(event) {
    event.preventDefault();

    if (!file) {
      setMessage("Chọn file PDF trước đã.");
      return;
    }

    setLoading(true);
    setMessage("Đang upload tài liệu...");

    try {
      await uploadDocument(file);
      setFile(null);
      setMessage("Upload thành công.");
      await loadDocuments();
    } catch (err) {
      setMessage(
        err.response?.data?.detail ||
          "Upload thất bại. Kiểm tra backend hoặc endpoint /documents/upload."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSign(doc) {
    const docId = doc.id || doc.doc_id;

    if (!docId) {
      setMessage("Không tìm thấy document id để ký.");
      return;
    }

    setSigningId(docId);
    setMessage("Đang ký tài liệu bằng FALCON-512...");

    try {
      await signDocument(docId);
      setMessage("Ký tài liệu thành công.");
      await loadDocuments();
    } catch (err) {
      setMessage(
        err.response?.data?.detail ||
          "Ký tài liệu thất bại. Kiểm tra quyền admin hoặc backend."
      );
    } finally {
      setSigningId(null);
    }
  }

  function shortHash(hash) {
    if (!hash) return "-";
    if (hash.length <= 20) return hash;
    return `${hash.slice(0, 12)}...${hash.slice(-8)}`;
  }

  return (
    <div>
      <h1>Danh sách tài liệu</h1>

      <p style={{ color: "#64748b" }}>
        Quản lý tài liệu đã upload và theo dõi trạng thái ký số FALCON.
      </p>

      <form onSubmit={handleUpload} style={styles.uploadBox}>
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />

        <button type="submit" disabled={loading} style={styles.primaryButton}>
          {loading ? "Đang xử lý..." : "Upload PDF"}
        </button>
      </form>

      {message && <p style={styles.message}>{message}</p>}

      {loading && <p>Đang tải...</p>}

      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>ID</th>
            <th style={styles.th}>Tên file</th>
            <th style={styles.th}>SHA-256</th>
            <th style={styles.th}>Trạng thái</th>
            <th style={styles.th}>Ngày upload</th>
            <th style={styles.th}>Thao tác</th>
          </tr>
        </thead>

        <tbody>
          {documents.length === 0 && (
            <tr>
              <td colSpan="6" style={styles.td}>
                Chưa có tài liệu hoặc backend chưa trả dữ liệu.
              </td>
            </tr>
          )}

          {documents.map((doc) => {
            const docId = doc.id || doc.doc_id;
            const filename = doc.filename || doc.fileName || "-";
            const hash = doc.file_hash || doc.fileHash || "-";
            const status = doc.status || "-";
            const createdAt = doc.created_at || doc.createdAt || "-";
            const isSigned = status === "signed";

            return (
              <tr key={docId}>
                <td style={{ ...styles.td, maxWidth: 180, wordBreak: "break-all" }}>
                  {docId}
                </td>

                <td style={styles.td}>{filename}</td>

                <td style={styles.td} title={hash}>
                  {shortHash(hash)}
                </td>

                <td style={styles.td}>
                  <span
                    style={{
                      ...styles.badge,
                      ...(isSigned ? styles.badgeSigned : styles.badgePending),
                    }}
                  >
                    {status}
                  </span>
                </td>

                <td style={styles.td}>
                  {createdAt !== "-"
                    ? new Date(createdAt).toLocaleString("vi-VN")
                    : "-"}
                </td>

                <td style={styles.td}>
                  <div style={styles.actions}>
                    <Link to={`/documents/${docId}`} style={styles.linkButton}>
                      Xem
                    </Link>

                    {isAdmin && !isSigned && (
                      <button
                        type="button"
                        onClick={() => handleSign(doc)}
                        disabled={signingId === docId}
                        style={styles.signButton}
                      >
                        {signingId === docId ? "Đang ký..." : "Ký FALCON"}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const styles = {
  uploadBox: {
    display: "flex",
    gap: 12,
    alignItems: "center",
    background: "white",
    padding: 16,
    borderRadius: 8,
    margin: "20px 0",
    border: "1px solid #e2e8f0",
  },
  message: {
    background: "#eff6ff",
    color: "#1e40af",
    padding: "10px 12px",
    borderRadius: 6,
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    background: "white",
    borderRadius: 8,
    overflow: "hidden",
  },
  th: {
    textAlign: "left",
    background: "#e2e8f0",
    padding: 10,
    borderBottom: "1px solid #cbd5e1",
  },
  td: {
    padding: 10,
    borderBottom: "1px solid #e2e8f0",
    verticalAlign: "top",
  },
  actions: {
    display: "flex",
    gap: 8,
    alignItems: "center",
    flexWrap: "wrap",
  },
  primaryButton: {
    background: "#1e3a8a",
    color: "white",
    border: 0,
    padding: "8px 12px",
    borderRadius: 6,
    cursor: "pointer",
  },
  linkButton: {
    color: "#1e3a8a",
    textDecoration: "none",
    fontWeight: 600,
  },
  signButton: {
    background: "#16a34a",
    color: "white",
    border: 0,
    padding: "7px 10px",
    borderRadius: 6,
    cursor: "pointer",
  },
  badge: {
    display: "inline-block",
    padding: "4px 8px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 700,
  },
  badgeSigned: {
    background: "#dcfce7",
    color: "#166534",
  },
  badgePending: {
    background: "#fef3c7",
    color: "#92400e",
  },
};