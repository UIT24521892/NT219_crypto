import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import {
  approveDocument,
  listDocuments,
  rejectDocument,
  signDocument,
  uploadDocument,
} from "../services/documents";
import { formatDate, getStatusLabel, getStatusTone } from "../utils/format";

export default function DocumentsListPage() {
  const { isAdmin } = useAuth();

  const [documents, setDocuments] = useState([]);
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("info");
  const [loading, setLoading] = useState(false);
  const [actionId, setActionId] = useState(null);

  async function loadDocuments() {
    setLoading(true);
    try {
      const data = await listDocuments({ limit: 100 });
      setDocuments(Array.isArray(data) ? data : data.items || data.documents || []);
    } catch (err) {
      setMessageType("error");
      setMessage(err.response?.data?.detail || "Không tải được danh sách tài liệu.");
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
      event.target.reset();
      setMessageType("success");
      setMessage("Upload thành công. Tài liệu đang ở trạng thái chờ duyệt.");
      await loadDocuments();
    } catch (err) {
      setMessageType("error");
      setMessage(err.response?.data?.detail || "Upload thất bại.");
    } finally {
      setLoading(false);
    }
  }

  async function runAction(doc, action) {
    const docId = doc.id || doc.doc_id;
    if (!docId) return;

    setActionId(`${action}:${docId}`);
    setMessageType("info");

    try {
      if (action === "approve") {
        setMessage("Đang duyệt hồ sơ...");
        await approveDocument(docId, "Hồ sơ đã được kiểm tra và đủ điều kiện ký.");
        setMessageType("success");
        setMessage("Đã duyệt hồ sơ. Bây giờ có thể ký FALCON.");
      }

      if (action === "reject") {
        const note = window.prompt("Nhập lý do từ chối:", "Hồ sơ chưa hợp lệ.") || "Hồ sơ chưa hợp lệ.";
        setMessage("Đang từ chối hồ sơ...");
        await rejectDocument(docId, note);
        setMessageType("success");
        setMessage("Đã từ chối hồ sơ.");
      }

      if (action === "sign") {
        setMessage("Đang ký tài liệu bằng FALCON-512...");
        await signDocument(docId);
        setMessageType("success");
        setMessage("Ký tài liệu thành công. Trạng thái đã chuyển sang đã ký.");
      }

      await loadDocuments();
    } catch (err) {
      setMessageType("error");
      setMessage(err.response?.data?.detail || `Thao tác ${action} thất bại.`);
    } finally {
      setActionId(null);
    }
  }

  function shortHash(hash) {
    if (!hash) return "-";
    if (hash.length <= 24) return hash;
    return `${hash.slice(0, 14)}...${hash.slice(-10)}`;
  }

  const counts = {
    total: documents.length,
    pending: documents.filter((doc) => doc.status === "pending_review").length,
    approved: documents.filter((doc) => doc.status === "approved").length,
    signed: documents.filter((doc) => doc.status === "signed").length,
  };

  return (
    <div>
      <div style={styles.pageHeader}>
        <div>
          <p style={styles.kicker}>Quản lý tài liệu</p>
          <h1 style={styles.title}>Danh sách tài liệu</h1>
          <p style={styles.subtitle}>
            Flow mới: upload → chờ duyệt → approved/rejected → ký FALCON → QR verify.
          </p>
        </div>
      </div>

      <div style={styles.statsGrid}>
        <StatCard label="Tổng tài liệu" value={counts.total} tone="blue" />
        <StatCard label="Chờ duyệt" value={counts.pending} tone="yellow" />
        <StatCard label="Đã duyệt" value={counts.approved} tone="blue" />
        <StatCard label="Đã ký" value={counts.signed} tone="green" />
      </div>

      <form onSubmit={handleUpload} style={styles.uploadBox}>
        <div>
          <p style={styles.uploadTitle}>Upload tài liệu PDF</p>
          <p style={styles.uploadSub}>Backend kiểm tra PDF magic bytes, lưu file và tính SHA-256.</p>
        </div>

        <div style={styles.uploadActions}>
          <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <button type="submit" disabled={loading} style={styles.primaryButton}>
            {loading ? "Đang xử lý..." : "Upload PDF"}
          </button>
        </div>
      </form>

      {message && <p style={{ ...styles.message, ...messageStyle(messageType) }}>{message}</p>}

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
                <td colSpan="6" style={styles.emptyTd}>Chưa có tài liệu.</td>
              </tr>
            )}

            {documents.map((doc) => {
              const docId = doc.id || doc.doc_id;
              const status = doc.status || "-";
              const tone = getStatusTone(status);
              const busy = actionId?.endsWith(`:${docId}`);

              return (
                <tr key={docId}>
                  <td style={styles.td}><span style={styles.docId}>{docId}</span></td>
                  <td style={styles.td}><strong>{doc.filename || "-"}</strong></td>
                  <td style={styles.td} title={doc.file_hash}><code style={styles.hash}>{shortHash(doc.file_hash)}</code></td>
                  <td style={styles.td}><span style={{ ...styles.badge, ...badgeStyle(tone) }}>{getStatusLabel(status)}</span></td>
                  <td style={styles.td}>{formatDate(doc.created_at)}</td>
                  <td style={styles.td}>
                    <div style={styles.actions}>
                      <Link to={`/documents/${docId}`} style={styles.linkButton}>Xem</Link>

                      {isAdmin && status === "pending_review" && (
                        <>
                          <button type="button" disabled={busy} onClick={() => runAction(doc, "approve")} style={styles.approveButton}>Duyệt</button>
                          <button type="button" disabled={busy} onClick={() => runAction(doc, "reject")} style={styles.rejectButton}>Từ chối</button>
                        </>
                      )}

                      {isAdmin && status === "approved" && (
                        <button type="button" disabled={busy} onClick={() => runAction(doc, "sign")} style={styles.signButton}>
                          {busy ? "Đang ký..." : "Ký FALCON"}
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
    </div>
  );
}

function StatCard({ label, value, tone }) {
  return (
    <div style={styles.statCard}>
      <p style={styles.statLabel}>{label}</p>
      <p style={{ ...styles.statValue, ...badgeStyle(tone) }}>{value}</p>
    </div>
  );
}

function badgeStyle(tone) {
  if (tone === "green") return { background: "#dcfce7", color: "#166534" };
  if (tone === "yellow") return { background: "#fef3c7", color: "#92400e" };
  if (tone === "red") return { background: "#fee2e2", color: "#991b1b" };
  if (tone === "blue") return { background: "#dbeafe", color: "#1d4ed8" };
  return { background: "#f1f5f9", color: "#475569" };
}

function messageStyle(type) {
  if (type === "success") return { background: "#ecfdf5", color: "#047857", borderColor: "#a7f3d0" };
  if (type === "error") return { background: "#fef2f2", color: "#b91c1c", borderColor: "#fecaca" };
  if (type === "warning") return { background: "#fffbeb", color: "#92400e", borderColor: "#fde68a" };
  return {};
}

const styles = {
  pageHeader: { display: "flex", justifyContent: "space-between", marginBottom: 20 },
  kicker: { margin: 0, color: "#8b1e1e", fontWeight: 900, textTransform: "uppercase", letterSpacing: 0.8, fontSize: 12 },
  title: { margin: "4px 0 0", fontSize: 32, color: "#111827" },
  subtitle: { margin: "8px 0 0", color: "#64748b" },
  statsGrid: { display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 14, marginBottom: 18 },
  statCard: { background: "white", border: "1px solid #e2e8f0", borderRadius: 14, padding: 16 },
  statLabel: { margin: 0, color: "#64748b", fontSize: 13, fontWeight: 800 },
  statValue: { margin: "10px 0 0", display: "inline-block", padding: "8px 12px", borderRadius: 999, fontSize: 22, fontWeight: 900 },
  uploadBox: { background: "white", border: "1px solid #e2e8f0", borderRadius: 16, padding: 18, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14, marginBottom: 14 },
  uploadTitle: { margin: 0, fontWeight: 900, color: "#111827" },
  uploadSub: { margin: "6px 0 0", color: "#64748b", fontSize: 14 },
  uploadActions: { display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" },
  primaryButton: { background: "#8b1e1e", color: "white", border: 0, borderRadius: 10, padding: "10px 14px", fontWeight: 800, cursor: "pointer" },
  message: { padding: "12px 14px", borderRadius: 12, background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe", fontWeight: 700 },
  tableCard: { background: "white", border: "1px solid #e2e8f0", borderRadius: 16, overflow: "auto", boxShadow: "0 8px 24px rgba(15,23,42,0.05)" },
  table: { width: "100%", borderCollapse: "collapse", minWidth: 980 },
  th: { textAlign: "left", padding: "14px 13px", background: "#f8fafc", color: "#475569", fontSize: 12, textTransform: "uppercase", letterSpacing: 0.5, borderBottom: "1px solid #e2e8f0" },
  td: { padding: "13px", borderBottom: "1px solid #f1f5f9", verticalAlign: "middle" },
  emptyTd: { padding: 30, textAlign: "center", color: "#64748b" },
  docId: { display: "inline-block", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontFamily: "monospace", fontSize: 12 },
  hash: { color: "#334155", background: "#f8fafc", padding: "4px 6px", borderRadius: 8 },
  badge: { display: "inline-block", padding: "6px 10px", borderRadius: 999, fontSize: 12, fontWeight: 900 },
  actions: { display: "flex", gap: 8, flexWrap: "wrap" },
  linkButton: { border: "1px solid #cbd5e1", color: "#334155", background: "white", borderRadius: 9, padding: "8px 10px", textDecoration: "none", fontWeight: 800 },
  approveButton: { background: "#1d4ed8", color: "white", border: 0, borderRadius: 9, padding: "8px 10px", fontWeight: 800, cursor: "pointer" },
  rejectButton: { background: "#b91c1c", color: "white", border: 0, borderRadius: 9, padding: "8px 10px", fontWeight: 800, cursor: "pointer" },
  signButton: { background: "#047857", color: "white", border: 0, borderRadius: 9, padding: "8px 10px", fontWeight: 800, cursor: "pointer" },
};
