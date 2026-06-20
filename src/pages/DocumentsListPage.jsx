import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listDocuments, uploadDocument } from "../services/documents";

const STATUS_META = {
  pending: { label: "Chờ", key: "badgePending" },
  pending_review: { label: "Chờ duyệt", key: "badgePending" },
  approved: { label: "Đã duyệt", key: "badgeApproved" },
  signed: { label: "Đã ký", key: "badgeSigned" },
  rejected: { label: "Bị từ chối", key: "badgeRejected" },
};

export default function DocumentsListPage() {
  const [documents, setDocuments] = useState([]);
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("info");
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
      setMessageType("error");
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
    // Fetching the initial document list on mount is intentional.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadDocuments();
  }, []);

  async function handleUpload(event) {
    event.preventDefault();

    if (!file) {
      setMessageType("warning");
      setMessage("Chọn file PDF trước đã.");
      return;
    }

    setLoading(true);
    setMessageType("info");
    setMessage("Đang upload tài liệu...");

    try {
      await uploadDocument(file);
      setFile(null);
      setMessageType("success");
      setMessage("Upload thành công. Backend đã tính SHA-256 cho tài liệu.");
      await loadDocuments();
    } catch (err) {
      setMessageType("error");
      setMessage(
        err.response?.data?.detail ||
          "Upload thất bại. Kiểm tra backend hoặc endpoint /documents/upload."
      );
    } finally {
      setLoading(false);
    }
  }

  function shortHash(hash) {
    if (!hash) return "-";
    if (hash.length <= 24) return hash;
    return `${hash.slice(0, 14)}...${hash.slice(-10)}`;
  }

  function formatDate(value) {
    if (!value) return "-";
    return new Date(value).toLocaleString("vi-VN");
  }

  const totalSigned = documents.filter((doc) => doc.status === "signed").length;
  const totalPending = documents.filter(
    (doc) => doc.status === "pending_review" || doc.status === "approved" || doc.status === "pending"
  ).length;

  return (
    <div>
      <div style={styles.pageHeader}>
        <div>
          <p style={styles.kicker}>Quản lý tài liệu</p>
          <h1 style={styles.title}>Danh sách tài liệu</h1>
          <p style={styles.subtitle}>
            Upload PDF, theo dõi SHA-256 hash và trạng thái duyệt/ký số ML-DSA-44.
          </p>
        </div>
      </div>

      <div style={styles.statsGrid}>
        <StatCard label="Tổng tài liệu" value={documents.length} tone="blue" />
        <StatCard label="Đã ký" value={totalSigned} tone="green" />
        <StatCard label="Chờ ký" value={totalPending} tone="yellow" />
      </div>

      <form onSubmit={handleUpload} style={styles.uploadBox}>
        <div>
          <p style={styles.uploadTitle}>Upload tài liệu PDF</p>
          <p style={styles.uploadSub}>
            Backend sẽ kiểm tra định dạng PDF và sinh SHA-256 hash.
          </p>
        </div>

        <div style={styles.uploadActions}>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />

          <button type="submit" disabled={loading} style={styles.primaryButton}>
            {loading ? "Đang xử lý..." : "Upload PDF"}
          </button>
        </div>
      </form>

      {message && (
        <p
          style={{
            ...styles.message,
            ...(messageType === "success" ? styles.messageSuccess : {}),
            ...(messageType === "error" ? styles.messageError : {}),
            ...(messageType === "warning" ? styles.messageWarning : {}),
          }}
        >
          {message}
        </p>
      )}

      <div style={styles.tableCard}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Mã tài liệu</th>
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
                <td colSpan="6" style={styles.emptyTd}>
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
              const statusMeta = STATUS_META[status] || {
                label: status,
                key: "badgePending",
              };

              return (
                <tr key={docId}>
                  <td style={styles.td}>
                    <span style={styles.docId}>{docId}</span>
                  </td>

                  <td style={styles.td}>
                    <strong>{filename}</strong>
                  </td>

                  <td style={styles.td} title={hash}>
                    <code style={styles.hash}>{shortHash(hash)}</code>
                  </td>

                  <td style={styles.td}>
                    <span style={{ ...styles.badge, ...styles[statusMeta.key] }}>
                      {statusMeta.label}
                    </span>
                  </td>

                  <td style={styles.td}>
                    {createdAt !== "-" ? formatDate(createdAt) : "-"}
                  </td>

                  <td style={styles.td}>
                    <div style={styles.actions}>
                      <Link to={`/documents/${docId}`} style={styles.linkButton}>
                        Xem
                      </Link>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({ label, value, tone }) {
  const toneStyle =
    tone === "green"
      ? { background: "#ecfdf5", color: "#047857" }
      : tone === "yellow"
      ? { background: "#fffbeb", color: "#92400e" }
      : { background: "#eff6ff", color: "#1d4ed8" };

  return (
    <div style={styles.statCard}>
      <p style={styles.statLabel}>{label}</p>
      <p style={{ ...styles.statValue, ...toneStyle }}>{value}</p>
    </div>
  );
}

const styles = {
  pageHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 20,
  },
  kicker: {
    margin: 0,
    color: "#8b1e1e",
    fontWeight: 900,
    textTransform: "uppercase",
    letterSpacing: 0.8,
    fontSize: 12,
  },
  title: {
    margin: "4px 0 0",
    fontSize: 32,
    color: "#111827",
  },
  subtitle: {
    margin: "8px 0 0",
    color: "#64748b",
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
    gap: 14,
    marginBottom: 18,
  },
  statCard: {
    background: "white",
    border: "1px solid #e2e8f0",
    borderRadius: 14,
    padding: 16,
  },
  statLabel: {
    margin: 0,
    color: "#64748b",
    fontSize: 13,
    fontWeight: 700,
  },
  statValue: {
    margin: "10px 0 0",
    width: 48,
    height: 48,
    borderRadius: 14,
    display: "grid",
    placeItems: "center",
    fontSize: 22,
    fontWeight: 900,
  },
  uploadBox: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 18,
    background: "white",
    padding: 18,
    borderRadius: 16,
    margin: "18px 0",
    border: "1px solid #e2e8f0",
    boxShadow: "0 8px 24px rgba(15,23,42,0.05)",
  },
  uploadTitle: {
    margin: 0,
    color: "#111827",
    fontWeight: 900,
  },
  uploadSub: {
    margin: "4px 0 0",
    color: "#64748b",
    fontSize: 13,
  },
  uploadActions: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  primaryButton: {
    background: "#8b1e1e",
    color: "white",
    border: 0,
    padding: "10px 14px",
    borderRadius: 10,
    cursor: "pointer",
    fontWeight: 800,
  },
  message: {
    padding: "12px 14px",
    borderRadius: 12,
    background: "#eff6ff",
    color: "#1d4ed8",
    border: "1px solid #bfdbfe",
    fontWeight: 650,
  },
  messageSuccess: {
    background: "#ecfdf5",
    color: "#047857",
    borderColor: "#a7f3d0",
  },
  messageError: {
    background: "#fef2f2",
    color: "#b91c1c",
    borderColor: "#fecaca",
  },
  messageWarning: {
    background: "#fffbeb",
    color: "#92400e",
    borderColor: "#fde68a",
  },
  tableCard: {
    background: "white",
    border: "1px solid #e2e8f0",
    borderRadius: 16,
    overflow: "hidden",
    boxShadow: "0 8px 24px rgba(15,23,42,0.05)",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
  },
  th: {
    textAlign: "left",
    background: "#f1f5f9",
    padding: 13,
    color: "#334155",
    fontSize: 13,
    borderBottom: "1px solid #dbe3ee",
  },
  td: {
    padding: 13,
    borderBottom: "1px solid #eef2f7",
    verticalAlign: "top",
    fontSize: 14,
  },
  emptyTd: {
    padding: 28,
    textAlign: "center",
    color: "#64748b",
  },
  docId: {
    display: "inline-block",
    maxWidth: 190,
    wordBreak: "break-all",
    color: "#475569",
    fontSize: 12,
  },
  hash: {
    color: "#7a1414",
    background: "#fff7ed",
    padding: "4px 6px",
    borderRadius: 6,
  },
  badge: {
    display: "inline-block",
    padding: "5px 10px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 900,
  },
  badgeSigned: {
    background: "#dcfce7",
    color: "#166534",
  },
  badgePending: {
    background: "#fef3c7",
    color: "#92400e",
  },
  badgeApproved: {
    background: "#dbeafe",
    color: "#1e40af",
  },
  badgeRejected: {
    background: "#fee2e2",
    color: "#991b1b",
  },
  actions: {
    display: "flex",
    gap: 8,
    alignItems: "center",
    flexWrap: "wrap",
  },
  linkButton: {
    color: "#8b1e1e",
    textDecoration: "none",
    fontWeight: 900,
  },
  signButton: {
    background: "#047857",
    color: "white",
    border: 0,
    padding: "8px 10px",
    borderRadius: 9,
    cursor: "pointer",
    fontWeight: 800,
  },
};
