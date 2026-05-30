import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import {
  getDocument,
  downloadDocument,
  getQrCode,
  getVerificationPackage,
  signDocument,
} from "../services/documents";

export default function DocumentDetailPage() {
  const { id } = useParams();
  const { isAdmin } = useAuth();

  const [doc, setDoc] = useState(null);
  const [qrUrl, setQrUrl] = useState("");
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("info");
  const [loading, setLoading] = useState(false);
  const [qrLoading, setQrLoading] = useState(false);
  const [signing, setSigning] = useState(false);

  const verifyUrl = `${window.location.origin}/verify?d=${id}`;

  const loadDocument = useCallback(async () => {
    setLoading(true);
    setMessage("");

    try {
      const data = await getDocument(id);
      setDoc(data);
    } catch (err) {
      setMessageType("error");
      setMessage(
        err.response?.data?.detail ||
          "Không tải được thông tin tài liệu. Kiểm tra backend hoặc document id."
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    // Fetching route-specific document state is intentional.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadDocument();
  }, [loadDocument]);

  useEffect(() => {
    return () => {
      if (qrUrl) URL.revokeObjectURL(qrUrl);
    };
  }, [qrUrl]);

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
      setMessageType("error");
      setMessage(
        err.response?.data?.detail ||
          "Tải file thất bại. Kiểm tra endpoint download."
      );
    }
  }

  async function handleSign() {
    setSigning(true);
    setMessageType("info");
    setMessage("Đang ký tài liệu bằng FALCON-512...");

    try {
      await signDocument(id);
      setMessageType("success");
      setMessage("Ký tài liệu thành công.");
      await loadDocument();
    } catch (err) {
      setMessageType("error");
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
      setMessageType("error");
      setMessage(
        err.response?.data?.detail ||
          "Không tạo được QR. Tài liệu phải được ký trước."
      );
    } finally {
      setQrLoading(false);
    }
  }

  async function handleDownloadVerificationPackage() {
    try {
      const verificationPackage = await getVerificationPackage(id);
      const blob = new Blob([JSON.stringify(verificationPackage, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${id}-verification-package.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setMessageType("error");
      setMessage(
        err.response?.data?.detail ||
          "Không xuất được verification package cho CLI offline."
      );
    }
  }

  function shortHash(hash) {
    if (!hash) return "-";
    if (hash.length <= 28) return hash;
    return `${hash.slice(0, 18)}...${hash.slice(-10)}`;
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
          <p style={styles.kicker}>Hồ sơ tài liệu</p>
          <h1 style={styles.title}>Chi tiết tài liệu</h1>
          <p style={styles.subtitle}>
            Theo dõi hash, trạng thái ký số và QR xác thực công khai.
          </p>
        </div>

        <Link to="/documents" style={styles.backLink}>
          ← Quay lại
        </Link>
      </div>

      {message && (
        <p
          style={{
            ...styles.message,
            ...(messageType === "success" ? styles.messageSuccess : {}),
            ...(messageType === "error" ? styles.messageError : {}),
          }}
        >
          {message}
        </p>
      )}

      <section style={styles.card}>
        <div style={styles.cardHeader}>
          <h2 style={styles.sectionTitle}>Thông tin định danh</h2>
          <span
            style={{
              ...styles.badge,
              ...(isSigned ? styles.badgeSigned : styles.badgePending),
            }}
          >
            {isSigned ? "Đã ký" : "Chờ ký"}
          </span>
        </div>

        <div style={styles.grid}>
          <Info label="Document ID" value={doc.id} breakText />
          <Info label="Tên file" value={doc.filename} />
          <Info label="Dung lượng" value={doc.file_size ? `${doc.file_size} bytes` : "-"} />
          <Info label="SHA-256" value={shortHash(doc.file_hash)} breakText />
          <Info label="Thuật toán" value="FALCON-512" />
          <Info label="Ngày upload" value={formatDate(doc.created_at)} />
          <Info label="Ngày ký" value={formatDate(doc.signed_at)} />
          <Info label="Public key ref" value={doc.public_key_ref || "-"} />
          <Info label="Người ký" value={doc.signer_email || doc.signed_by || "-"} />
        </div>
      </section>

      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>Thao tác tài liệu</h2>

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

              <button
                type="button"
                onClick={handleDownloadVerificationPackage}
                style={styles.btnOutline}
              >
                Tải verification package
              </button>
            </>
          )}
        </div>

        {!isSigned && (
          <p style={styles.note}>
            Tài liệu đang chờ ký. Admin cần ký FALCON trước khi tạo QR.
          </p>
        )}
      </section>

      {isSigned && (
        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>QR xác thực</h2>

          <p style={styles.note}>Đường dẫn xác thực công khai:</p>
          <p style={styles.verifyLink}>{verifyUrl}</p>

          {qrUrl ? (
            <div style={styles.qrBox}>
              <img src={qrUrl} alt="Document QR Code" style={styles.qrImage} />
            </div>
          ) : (
            <p style={styles.note}>Bấm “Xem QR” để lấy ảnh QR từ backend.</p>
          )}
        </section>
      )}
    </div>
  );
}

function Info({ label, value, breakText }) {
  return (
    <div style={styles.infoItem}>
      <p style={styles.label}>{label}</p>
      <p style={breakText ? styles.valueBreak : styles.value}>{value || "-"}</p>
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
    color: "#64748b",
    marginTop: 6,
  },
  backLink: {
    color: "#8b1e1e",
    fontWeight: 900,
    textDecoration: "none",
  },
  card: {
    background: "white",
    border: "1px solid #e2e8f0",
    borderRadius: 16,
    padding: 20,
    marginBottom: 18,
    boxShadow: "0 8px 24px rgba(15,23,42,0.05)",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
    marginBottom: 16,
  },
  sectionTitle: {
    margin: 0,
    fontSize: 20,
    color: "#111827",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    gap: 14,
  },
  infoItem: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 12,
    padding: 13,
  },
  label: {
    margin: "0 0 5px",
    color: "#64748b",
    fontSize: 12,
    fontWeight: 900,
    textTransform: "uppercase",
  },
  value: {
    margin: 0,
    color: "#111827",
    fontWeight: 700,
  },
  valueBreak: {
    margin: 0,
    color: "#111827",
    wordBreak: "break-all",
    fontWeight: 700,
  },
  badge: {
    display: "inline-block",
    padding: "6px 11px",
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
  actions: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  },
  btnBlue: {
    background: "#1e3a8a",
    color: "white",
    border: 0,
    borderRadius: 10,
    padding: "10px 14px",
    cursor: "pointer",
    fontWeight: 800,
  },
  btnGreen: {
    background: "#047857",
    color: "white",
    border: 0,
    borderRadius: 10,
    padding: "10px 14px",
    cursor: "pointer",
    fontWeight: 800,
  },
  btnOutline: {
    border: "1px solid #8b1e1e",
    color: "#8b1e1e",
    background: "white",
    borderRadius: 10,
    padding: "10px 14px",
    textDecoration: "none",
    fontWeight: 900,
  },
  note: {
    color: "#64748b",
    marginBottom: 0,
  },
  verifyLink: {
    background: "#fff7ed",
    border: "1px solid #fed7aa",
    padding: 12,
    borderRadius: 10,
    wordBreak: "break-all",
    color: "#8b1e1e",
    fontWeight: 800,
  },
  qrBox: {
    marginTop: 16,
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 14,
    padding: 20,
    display: "inline-block",
  },
  qrImage: {
    width: 230,
    height: 230,
    objectFit: "contain",
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
  error: {
    background: "#fee2e2",
    color: "#991b1b",
    padding: "10px 12px",
    borderRadius: 10,
  },
};
