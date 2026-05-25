import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import {
  getDocument,
  downloadDocument,
  getQrCode,
  signDocument,
} from "../services/documents";

export default function DocumentDetailPage() {
  const { id } = useParams();
  const { isAdmin } = useAuth();

  const [doc, setDoc] = useState(null);
  const [qrUrl, setQrUrl] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [qrLoading, setQrLoading] = useState(false);
  const [signing, setSigning] = useState(false);

  const verifyUrl = `${window.location.origin}/verify?d=${id}`;

  async function loadDocument() {
    setLoading(true);
    setMessage("");

    try {
      const data = await getDocument(id);
      setDoc(data);
    } catch (err) {
      setMessage(
        err.response?.data?.detail ||
          "Không tải được thông tin tài liệu. Kiểm tra backend hoặc document id."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocument();
  }, [id]);

  async function handleDownload() {
    try {
      const blob = await downloadDocument(id);
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = doc?.filename || "document.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();

      URL.revokeObjectURL(url);
    } catch (err) {
      setMessage(
        err.response?.data?.detail ||
          "Tải file thất bại. Kiểm tra endpoint download."
      );
    }
  }

  async function handleSign() {
    setSigning(true);
    setMessage("Đang ký tài liệu bằng FALCON-512...");

    try {
      await signDocument(id);
      setMessage("Ký tài liệu thành công.");
      await loadDocument();
    } catch (err) {
      setMessage(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          `Ký thất bại. Status: ${err.response?.status || "Network Error"}`
      );
    } finally {
      setSigning(false);
    }
  }

  async function handleShowQr() {
    setQrLoading(true);
    setMessage("");

    try {
      const url = await getQrCode(id);
      setQrUrl(url);
    } catch (err) {
      setMessage(
        err.response?.data?.detail ||
          "Không tạo được QR. Tài liệu phải được ký trước."
      );
    } finally {
      setQrLoading(false);
    }
  }

  function shortHash(hash) {
    if (!hash) return "-";
    if (hash.length <= 24) return hash;
    return `${hash.slice(0, 16)}...${hash.slice(-10)}`;
  }

  function formatDate(value) {
    if (!value) return "-";
    return new Date(value).toLocaleString("vi-VN");
  }

  if (loading) {
    return <p>Đang tải chi tiết tài liệu...</p>;
  }

  if (!doc) {
    return (
      <div>
        <h1>Chi tiết tài liệu</h1>
        {message && <p style={styles.error}>{message}</p>}
        <Link to="/documents">← Quay lại danh sách</Link>
      </div>
    );
  }

  const status = doc.status || "-";
  const isSigned = status === "signed";

  return (
    <div>
      <div style={styles.header}>
        <div>
          <h1>Chi tiết tài liệu</h1>
          <p style={styles.subtitle}>
            Xem thông tin hash, chữ ký số FALCON và QR xác thực tài liệu.
          </p>
        </div>

        <Link to="/documents" style={styles.backLink}>
          ← Quay lại
        </Link>
      </div>

      {message && <p style={styles.message}>{message}</p>}

      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>Thông tin tài liệu</h2>

        <div style={styles.grid}>
          <div>
            <p style={styles.label}>Document ID</p>
            <p style={styles.valueBreak}>{doc.id}</p>
          </div>

          <div>
            <p style={styles.label}>Tên file</p>
            <p style={styles.value}>{doc.filename || "-"}</p>
          </div>

          <div>
            <p style={styles.label}>Dung lượng</p>
            <p style={styles.value}>
              {doc.file_size ? `${doc.file_size} bytes` : "-"}
            </p>
          </div>

          <div>
            <p style={styles.label}>Trạng thái</p>
            <span
              style={{
                ...styles.badge,
                ...(isSigned ? styles.badgeSigned : styles.badgePending),
              }}
            >
              {status}
            </span>
          </div>

          <div>
            <p style={styles.label}>SHA-256 hash</p>
            <p style={styles.valueBreak} title={doc.file_hash}>
              {shortHash(doc.file_hash)}
            </p>
          </div>

          <div>
            <p style={styles.label}>Thuật toán</p>
            <p style={styles.value}>FALCON-512</p>
          </div>

          <div>
            <p style={styles.label}>Ngày upload</p>
            <p style={styles.value}>{formatDate(doc.created_at)}</p>
          </div>

          <div>
            <p style={styles.label}>Ngày ký</p>
            <p style={styles.value}>{formatDate(doc.signed_at)}</p>
          </div>

          <div>
            <p style={styles.label}>Public key ref</p>
            <p style={styles.value}>{doc.public_key_ref || "-"}</p>
          </div>

          <div>
            <p style={styles.label}>Người ký</p>
            <p style={styles.value}>{doc.signer_email || doc.signed_by || "-"}</p>
          </div>
        </div>
      </section>

      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>Thao tác</h2>

        <div style={styles.actions}>
          <button type="button" onClick={handleDownload} style={styles.btnBlue}>
            Tải PDF
          </button>

          {isAdmin && !isSigned && (
            <button
              type="button"
              onClick={handleSign}
              disabled={signing}
              style={styles.btnGreen}
            >
              {signing ? "Đang ký..." : "Ký FALCON"}
            </button>
          )}

          {isSigned && (
            <>
              <button
                type="button"
                onClick={handleShowQr}
                disabled={qrLoading}
                style={styles.btnGreen}
              >
                {qrLoading ? "Đang tạo QR..." : "Xem QR"}
              </button>

              <Link to={`/verify?d=${id}`} style={styles.btnOutline}>
                Mở trang Verify
              </Link>
            </>
          )}
        </div>

        {!isSigned && (
          <p style={styles.note}>
            Tài liệu đang ở trạng thái pending. Cần admin ký FALCON trước khi tạo QR.
          </p>
        )}
      </section>

      {isSigned && (
        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>QR xác thực</h2>

          <p style={styles.note}>
            QR sẽ trỏ về trang verify public:
          </p>

          <p style={styles.verifyLink}>{verifyUrl}</p>

          {qrUrl ? (
            <div style={styles.qrBox}>
              <img src={qrUrl} alt="Document QR Code" style={styles.qrImage} />
            </div>
          ) : (
            <p style={styles.note}>
              Bấm “Xem QR” để lấy ảnh QR từ backend.
            </p>
          )}
        </section>
      )}
    </div>
  );
}

const styles = {
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 16,
    marginBottom: 20,
  },
  subtitle: {
    color: "#64748b",
    marginTop: 4,
  },
  backLink: {
    color: "#1e3a8a",
    fontWeight: 600,
    textDecoration: "none",
  },
  card: {
    background: "white",
    border: "1px solid #e2e8f0",
    borderRadius: 10,
    padding: 20,
    marginBottom: 18,
  },
  sectionTitle: {
    marginTop: 0,
    marginBottom: 16,
    fontSize: 20,
    color: "#0f172a",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    gap: 16,
  },
  label: {
    margin: "0 0 4px",
    color: "#64748b",
    fontSize: 13,
    fontWeight: 600,
  },
  value: {
    margin: 0,
    color: "#0f172a",
  },
  valueBreak: {
    margin: 0,
    color: "#0f172a",
    wordBreak: "break-all",
  },
  badge: {
    display: "inline-block",
    padding: "5px 10px",
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
  actions: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  },
  btnBlue: {
    background: "#1e3a8a",
    color: "white",
    border: 0,
    borderRadius: 6,
    padding: "10px 14px",
    cursor: "pointer",
    fontWeight: 600,
  },
  btnGreen: {
    background: "#16a34a",
    color: "white",
    border: 0,
    borderRadius: 6,
    padding: "10px 14px",
    cursor: "pointer",
    fontWeight: 600,
  },
  btnOutline: {
    border: "1px solid #1e3a8a",
    color: "#1e3a8a",
    background: "white",
    borderRadius: 6,
    padding: "10px 14px",
    textDecoration: "none",
    fontWeight: 600,
  },
  note: {
    color: "#64748b",
    marginBottom: 0,
  },
  verifyLink: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    padding: 10,
    borderRadius: 6,
    wordBreak: "break-all",
    color: "#1e3a8a",
  },
  qrBox: {
    marginTop: 16,
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 10,
    padding: 20,
    display: "inline-block",
  },
  qrImage: {
    width: 220,
    height: 220,
    objectFit: "contain",
  },
  message: {
    background: "#eff6ff",
    color: "#1e40af",
    padding: "10px 12px",
    borderRadius: 6,
    marginBottom: 16,
  },
  error: {
    background: "#fee2e2",
    color: "#991b1b",
    padding: "10px 12px",
    borderRadius: 6,
    marginBottom: 16,
  },
};