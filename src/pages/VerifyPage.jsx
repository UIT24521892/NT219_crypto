import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { verifyDocument } from "../services/verify";

export default function VerifyPage() {
  const [params] = useSearchParams();
  const docId = params.get("d");

  const [manualId, setManualId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function runVerify(id) {
    if (!id) {
      setError("Thiếu mã tài liệu trong URL hoặc ô nhập.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await verifyDocument(id);
      setResult(data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Không thể xác minh tài liệu. Kiểm tra mã tài liệu hoặc backend."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (docId) {
      // Verify the document automatically when a scanned URL is opened.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      runVerify(docId);
    }
  }, [docId]);

  function handleManualVerify(event) {
    event.preventDefault();
    const id = manualId.trim();
    if (!id) return;
    window.location.href = `/verify?d=${encodeURIComponent(id)}`;
  }

  const isValid = result?.valid === true;

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div style={styles.emblem}>✓</div>
          <div>
            <p style={styles.kicker}>Public Verification</p>
            <h1 style={styles.title}>Cổng xác thực tài liệu</h1>
            <p style={styles.subtitle}>
              Kiểm tra tính hợp lệ của tài liệu đã ký bằng FALCON-512.
            </p>
          </div>
        </div>

        {!docId && (
          <form onSubmit={handleManualVerify} style={styles.manualBox}>
            <p style={styles.manualTitle}>Nhập mã tài liệu để kiểm tra</p>

            <div style={styles.manualRow}>
              <input
                value={manualId}
                onChange={(e) => setManualId(e.target.value)}
                placeholder="Nhập document_id..."
                style={styles.input}
              />

              <button type="submit" style={styles.btnPrimary}>
                Xác thực
              </button>
            </div>

            <p style={styles.note}>
              QR code sẽ tự mở trang dạng <code>/verify?d=&lt;document_id&gt;</code>.
            </p>
          </form>
        )}

        {loading && <div style={styles.infoBox}>Đang xác minh tài liệu...</div>}

        {error && (
          <div style={styles.warningBox}>
            <h2 style={styles.boxTitle}>❌ Không thể xác minh</h2>
            <p style={styles.boxText}>{error}</p>
          </div>
        )}

        {result && (
          <div style={isValid ? styles.successBox : styles.dangerBox}>
            <h2 style={styles.boxTitle}>
              {isValid ? "✅ Tài liệu hợp lệ" : "❌ Tài liệu không hợp lệ"}
            </h2>

            <p style={styles.boxText}>
              {isValid
                ? "Chữ ký FALCON-512 đã được xác minh thành công."
                : result.reason || "Backend trả kết quả invalid."}
            </p>

            <div style={styles.resultGrid}>
              <Info label="Document ID" value={result.doc_id} />
              <Info label="Tên file" value={result.filename} />
              <Info label="Trạng thái" value={result.status} />
              <Info label="Người ký" value={result.signer_email || "-"} />
              <Info label="Thời gian ký" value={formatDate(result.signed_at)} />
              <Info label="Public key ref" value={result.public_key_ref || "-"} />
              <Info label="SHA-256" value={result.file_hash} wide />
            </div>
          </div>
        )}

        <div style={styles.footer}>
          <Link to="/login" style={styles.link}>
            Về trang đăng nhập
          </Link>
        </div>
      </div>
    </div>
  );
}

function Info({ label, value, wide }) {
  return (
    <div style={wide ? styles.infoWide : styles.infoItem}>
      <p style={styles.infoLabel}>{label}</p>
      <p style={styles.infoValue}>{value || "-"}</p>
    </div>
  );
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("vi-VN");
}

const styles = {
  page: {
    minHeight: "100vh",
    background:
      "radial-gradient(circle at top left, #fff1f2 0, #f3f5f8 38%, #eef2f7 100%)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  card: {
    width: "100%",
    maxWidth: 760,
    background: "white",
    borderRadius: 20,
    padding: 30,
    border: "1px solid #e5e7eb",
    boxShadow: "0 18px 50px rgba(15,23,42,0.12)",
  },
  header: {
    display: "flex",
    gap: 14,
    alignItems: "center",
    marginBottom: 22,
  },
  emblem: {
    width: 54,
    height: 54,
    borderRadius: 16,
    background: "#8b1e1e",
    color: "white",
    display: "grid",
    placeItems: "center",
    fontSize: 27,
    fontWeight: 900,
  },
  kicker: {
    margin: 0,
    color: "#8b1e1e",
    fontWeight: 900,
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  title: {
    margin: "4px 0 0",
    color: "#111827",
    fontSize: 28,
  },
  subtitle: {
    margin: "5px 0 0",
    color: "#64748b",
  },
  manualBox: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 14,
    padding: 16,
    marginBottom: 18,
  },
  manualTitle: {
    margin: "0 0 10px",
    fontWeight: 900,
    color: "#111827",
  },
  manualRow: {
    display: "flex",
    gap: 10,
  },
  input: {
    flex: 1,
    padding: "11px 12px",
    borderRadius: 10,
    border: "1px solid #cbd5e1",
    fontSize: 14,
  },
  btnPrimary: {
    background: "#8b1e1e",
    color: "white",
    border: 0,
    borderRadius: 10,
    padding: "0 16px",
    fontWeight: 800,
    cursor: "pointer",
  },
  note: {
    color: "#64748b",
    fontSize: 13,
    marginBottom: 0,
  },
  infoBox: {
    background: "#eff6ff",
    color: "#1d4ed8",
    border: "1px solid #bfdbfe",
    padding: 14,
    borderRadius: 14,
    fontWeight: 800,
  },
  warningBox: {
    background: "#fffbeb",
    border: "1px solid #facc15",
    color: "#92400e",
    padding: 18,
    borderRadius: 16,
  },
  successBox: {
    background: "#ecfdf5",
    border: "1px solid #a7f3d0",
    color: "#065f46",
    padding: 18,
    borderRadius: 16,
  },
  dangerBox: {
    background: "#fef2f2",
    border: "1px solid #fecaca",
    color: "#991b1b",
    padding: 18,
    borderRadius: 16,
  },
  boxTitle: {
    margin: 0,
    fontSize: 22,
  },
  boxText: {
    marginTop: 8,
  },
  resultGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    gap: 12,
    marginTop: 16,
  },
  infoItem: {
    background: "rgba(255,255,255,0.76)",
    border: "1px solid rgba(15,23,42,0.08)",
    borderRadius: 12,
    padding: 12,
  },
  infoWide: {
    gridColumn: "1 / -1",
    background: "rgba(255,255,255,0.76)",
    border: "1px solid rgba(15,23,42,0.08)",
    borderRadius: 12,
    padding: 12,
  },
  infoLabel: {
    margin: 0,
    color: "#64748b",
    fontSize: 12,
    fontWeight: 800,
    textTransform: "uppercase",
  },
  infoValue: {
    margin: "6px 0 0",
    color: "#111827",
    wordBreak: "break-all",
    fontWeight: 650,
  },
  footer: {
    marginTop: 18,
    textAlign: "center",
  },
  link: {
    color: "#8b1e1e",
    fontWeight: 800,
    textDecoration: "none",
  },
};
