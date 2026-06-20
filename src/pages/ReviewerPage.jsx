import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listDocuments, approveDocument, rejectDocument } from "../services/documents";

export default function ReviewerPage() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [notes, setNotes] = useState({});
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("info");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listDocuments({ limit: 100 });
      const list = Array.isArray(data) ? data : [];
      setDocs(list.filter((d) => d.status === "pending_review"));
    } catch (err) {
      setMessageType("error");
      setMessage(err.response?.data?.detail || "Không tải được hàng chờ duyệt.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function handleApprove(id) {
    setBusyId(id);
    setMessage("");
    try {
      await approveDocument(id, notes[id]);
      setMessageType("success");
      setMessage("Đã phê duyệt tài liệu. Chuyển sang hàng chờ ký.");
      await load();
    } catch (err) {
      setMessageType("error");
      setMessage(err.response?.data?.detail || "Phê duyệt thất bại.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleReject(id) {
    const note = (notes[id] || "").trim();
    if (!note) {
      setMessageType("warning");
      setMessage("Phải nhập lý do từ chối.");
      return;
    }
    setBusyId(id);
    setMessage("");
    try {
      await rejectDocument(id, note);
      setMessageType("success");
      setMessage("Đã từ chối tài liệu.");
      await load();
    } catch (err) {
      setMessageType("error");
      setMessage(err.response?.data?.detail || "Từ chối thất bại.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <p style={styles.kicker}>Reviewer</p>
      <h1 style={styles.title}>Hàng chờ duyệt</h1>
      <p style={styles.subtitle}>
        Người duyệt phê duyệt hoặc từ chối hồ sơ. Người ký không trùng người duyệt
        (tách biệt trách nhiệm).
      </p>

      {message && (
        <p
          style={{
            ...styles.message,
            ...(messageType === "success" ? styles.msgOk : {}),
            ...(messageType === "error" ? styles.msgErr : {}),
            ...(messageType === "warning" ? styles.msgWarn : {}),
          }}
        >
          {message}
        </p>
      )}

      {loading ? (
        <p>Đang tải...</p>
      ) : docs.length === 0 ? (
        <p style={styles.empty}>Không có tài liệu nào đang chờ duyệt.</p>
      ) : (
        <div style={styles.list}>
          {docs.map((doc) => (
            <div key={doc.id} style={styles.card}>
              <div style={styles.cardTop}>
                <div>
                  <Link to={`/documents/${doc.id}`} style={styles.docLink}>
                    {doc.filename}
                  </Link>
                  <p style={styles.meta}>SHA-256: {doc.file_hash?.slice(0, 24)}…</p>
                </div>
                <span style={styles.badge}>Chờ duyệt</span>
              </div>

              <textarea
                value={notes[doc.id] || ""}
                onChange={(e) => setNotes((n) => ({ ...n, [doc.id]: e.target.value }))}
                placeholder="Ghi chú duyệt / lý do từ chối..."
                style={styles.textarea}
              />

              <div style={styles.actions}>
                <button
                  type="button"
                  onClick={() => handleApprove(doc.id)}
                  disabled={busyId === doc.id}
                  style={styles.btnGreen}
                >
                  {busyId === doc.id ? "..." : "Phê duyệt"}
                </button>
                <button
                  type="button"
                  onClick={() => handleReject(doc.id)}
                  disabled={busyId === doc.id}
                  style={styles.btnRed}
                >
                  Từ chối
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  kicker: { margin: 0, color: "#8b1e1e", fontWeight: 900, textTransform: "uppercase", letterSpacing: 0.8, fontSize: 12 },
  title: { margin: "4px 0 0", fontSize: 30, color: "#111827" },
  subtitle: { color: "#64748b", marginTop: 6, marginBottom: 18 },
  list: { display: "flex", flexDirection: "column", gap: 14 },
  card: { background: "white", border: "1px solid #e2e8f0", borderRadius: 14, padding: 16 },
  cardTop: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 },
  docLink: { fontWeight: 800, color: "#111827", textDecoration: "none", fontSize: 16 },
  meta: { color: "#64748b", margin: "4px 0 0", fontSize: 13 },
  badge: { background: "#fef3c7", color: "#92400e", padding: "5px 10px", borderRadius: 999, fontSize: 12, fontWeight: 900 },
  textarea: { width: "100%", marginTop: 12, minHeight: 60, padding: 10, borderRadius: 10, border: "1px solid #cbd5e1", fontFamily: "inherit", fontSize: 14, boxSizing: "border-box" },
  actions: { display: "flex", gap: 10, marginTop: 12 },
  btnGreen: { background: "#047857", color: "white", border: 0, borderRadius: 10, padding: "10px 16px", fontWeight: 800, cursor: "pointer" },
  btnRed: { background: "#b91c1c", color: "white", border: 0, borderRadius: 10, padding: "10px 16px", fontWeight: 800, cursor: "pointer" },
  empty: { color: "#64748b", background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: 12, padding: 24, textAlign: "center" },
  message: { padding: "12px 14px", borderRadius: 12, background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe", fontWeight: 650 },
  msgOk: { background: "#ecfdf5", color: "#047857", borderColor: "#a7f3d0" },
  msgErr: { background: "#fef2f2", color: "#b91c1c", borderColor: "#fecaca" },
  msgWarn: { background: "#fffbeb", color: "#92400e", borderColor: "#fde68a" },
};
