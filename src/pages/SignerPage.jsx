import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import { listDocuments, signDocument } from "../services/documents";

export default function SignerPage() {
  const { agencyId, isAdmin } = useAuth();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("info");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listDocuments({ limit: 100 });
      const list = Array.isArray(data) ? data : [];
      setDocs(list.filter((d) => d.status === "approved"));
    } catch (err) {
      setMessageType("error");
      setMessage(err.response?.data?.detail || "Không tải được hàng chờ ký.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function handleSign(id) {
    setBusyId(id);
    setMessage("");
    try {
      await signDocument(id);
      setMessageType("success");
      setMessage("Đã ký ML-DSA-44 + QR Ed25519. Tài liệu chuyển sang 'Đã ký'.");
      await load();
    } catch (err) {
      const detail = err.response?.data?.detail || "Ký thất bại.";
      setMessageType("error");
      // Surface separation-of-duty / not-approved conflicts clearly.
      setMessage(
        err.response?.status === 403
          ? `Bị từ chối: ${detail} (người duyệt không được tự ký).`
          : detail
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <p style={styles.kicker}>Signer</p>
      <h1 style={styles.title}>Hàng chờ ký</h1>
      <p style={styles.subtitle}>
        Người ký áp chữ ký hậu lượng tử ML-DSA-44 và chữ ký QR Ed25519 lên hồ sơ đã
        được duyệt. Không thể ký hồ sơ do chính mình duyệt.
      </p>

      {agencyId == null && !isAdmin && (
        <p style={{ ...styles.message, ...styles.msgErr }}>
          Bạn chưa được gán cơ quan nào nên không thể ký. Liên hệ admin để được gán
          cơ quan (mục “Quản lý cơ quan”).
        </p>
      )}

      {message && (
        <p
          style={{
            ...styles.message,
            ...(messageType === "success" ? styles.msgOk : {}),
            ...(messageType === "error" ? styles.msgErr : {}),
          }}
        >
          {message}
        </p>
      )}

      {loading ? (
        <p>Đang tải...</p>
      ) : docs.length === 0 ? (
        <p style={styles.empty}>Không có tài liệu nào đã duyệt đang chờ ký.</p>
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
                  {doc.review_note && (
                    <p style={styles.note}>Ghi chú duyệt: {doc.review_note}</p>
                  )}
                </div>
                <span style={styles.badge}>Đã duyệt</span>
              </div>

              <div style={styles.actions}>
                <button
                  type="button"
                  onClick={() => handleSign(doc.id)}
                  disabled={busyId === doc.id}
                  style={styles.btnGreen}
                >
                  {busyId === doc.id ? "Đang ký..." : "Ký ML-DSA-44"}
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
  note: { color: "#475569", margin: "6px 0 0", fontSize: 13, fontStyle: "italic" },
  badge: { background: "#dbeafe", color: "#1e40af", padding: "5px 10px", borderRadius: 999, fontSize: 12, fontWeight: 900 },
  actions: { display: "flex", gap: 10, marginTop: 12 },
  btnGreen: { background: "#047857", color: "white", border: 0, borderRadius: 10, padding: "10px 16px", fontWeight: 800, cursor: "pointer" },
  empty: { color: "#64748b", background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: 12, padding: 24, textAlign: "center" },
  message: { padding: "12px 14px", borderRadius: 12, background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe", fontWeight: 650 },
  msgOk: { background: "#ecfdf5", color: "#047857", borderColor: "#a7f3d0" },
  msgErr: { background: "#fef2f2", color: "#b91c1c", borderColor: "#fecaca" },
};
