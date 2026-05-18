import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listDocuments, uploadDocument } from "../services/documents";

export default function DocumentsListPage() {
  const [documents, setDocuments] = useState([]);
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

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
      setMessage("Chưa kết nối được backend hoặc API /documents lỗi.");
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
      setMessage("Upload thất bại. Kiểm tra backend hoặc endpoint /documents/upload.");
    } finally {
      setLoading(false);
    }
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

        <button type="submit" disabled={loading}>
          Upload PDF
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
            <th style={styles.th}>Chi tiết</th>
          </tr>
        </thead>

        <tbody>
          {documents.length === 0 && (
            <tr>
              <td colSpan="5" style={styles.td}>
                Chưa có tài liệu hoặc backend chưa trả dữ liệu.
              </td>
            </tr>
          )}

          {documents.map((doc) => (
            <tr key={doc.id || doc.doc_id}>
              <td style={styles.td}>{doc.id || doc.doc_id}</td>
              <td style={styles.td}>{doc.filename || doc.fileName || "-"}</td>
              <td style={{ ...styles.td, wordBreak: "break-all", maxWidth: 260 }}>
                {doc.file_hash || doc.fileHash || "-"}
              </td>
              <td style={styles.td}>{doc.status || "-"}</td>
              <td style={styles.td}>
                <Link to={`/documents/${doc.id || doc.doc_id}`}>Xem</Link>
              </td>
            </tr>
          ))}
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
  },
};