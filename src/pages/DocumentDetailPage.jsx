import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import {
  getDocument,
  downloadDocument,
  downloadSignedDocument,
  getQrCode,
  getVerificationPackage,
  signDocument,
  approveDocument,
  rejectDocument,
} from "../services/documents";

export default function DocumentDetailPage() {
  const { id } = useParams();
  const { isReviewer, isSigner } = useAuth();

  const [doc, setDoc] = useState(null);
  const [qrUrl, setQrUrl] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("info");
  const [loading, setLoading] = useState(false);
  const [qrLoading, setQrLoading] = useState(false);
  const [signing, setSigning] = useState(false);
  const [reviewing, setReviewing] = useState(false);

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
    setMessage("Đang ký tài liệu bằng ML-DSA-44 + QR Ed25519...");

    try {
      await signDocument(id);
      setMessageType("success");
      setMessage("Ký tài liệu thành công.");
      await loadDocument();
    } catch (err) {
      setMessageType("error");
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        `Ký thất bại. Status: ${err.response?.status || "Network Error"}`;
      setMessage(
        err.response?.status === 403
          ? `Bị từ chối: ${detail} (người duyệt không được tự ký).`
          : detail
      );
    } finally {
      setSigning(false);
    }
  }

  async function handleApprove() {
    setReviewing(true);
    setMessageType("info");
    setMessage("Đang phê duyệt...");

    try {
      await approveDocument(id, reviewNote);
      setMessageType("success");
      setMessage("Đã phê duyệt. Tài liệu chuyển sang hàng chờ ký.");
      setReviewNote("");
      await loadDocument();
    } catch (err) {
      setMessageType("error");
      setMessage(err.response?.data?.detail || "Phê duyệt thất bại.");
    } finally {
      setReviewing(false);
    }
  }

  async function handleReject() {
    const note = reviewNote.trim();
    if (!note) {
      setMessageType("error");
      setMessage("Phải nhập lý do từ chối.");
      return;
    }
    setReviewing(true);
    setMessageType("info");
    setMessage("Đang từ chối...");

    try {
      await rejectDocument(id, note);
      setMessageType("success");
      setMessage("Đã từ chối tài liệu.");
      setReviewNote("");
      await loadDocument();
    } catch (err) {
      setMessageType("error");
      setMessage(err.response?.data?.detail || "Từ chối thất bại.");
    } finally {
      setReviewing(false);
    }
  }

  async function handleDownloadSigned() {
    try {
      const blob = await downloadSignedDocument(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(doc?.filename || "document").replace(/\.pdf$/i, "")}_signed.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setMessageType("error");
      setMessage(
        err.response?.data?.detail ||
          "Không tải được PDF đã ký (QR + chữ ký nhúng)."
      );
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
  const isPendingReview = status === "pending_review";
  const isApproved = status === "approved";
  const isRejected = status === "rejected";

  const STATUS_META = {
    pending_review: { label: "Chờ duyệt", style: styles.badgePending },
    approved: { label: "Đã duyệt", style: styles.badgeApproved },
    signed: { label: "Đã ký", style: styles.badgeSigned },
    rejected: { label: "Bị từ chối", style: styles.badgeRejected },
  };
  const statusMeta = STATUS_META[status] || { label: status, style: styles.badgePending };

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
          <span style={{ ...styles.badge, ...statusMeta.style }}>
            {statusMeta.label}
          </span>
        </div>

        <div style={styles.grid}>
          <Info label="Document ID" value={doc.id} breakText />
          <Info label="Tên file" value={doc.filename} />
          <Info label="Dung lượng" value={doc.file_size ? `${doc.file_size} bytes` : "-"} />
          <Info label="SHA-256" value={shortHash(doc.file_hash)} breakText />
          <Info label="Thuật toán" value="ML-DSA-44 (PQC) + Ed25519 (QR)" />
          <Info label="Ngày upload" value={formatDate(doc.created_at)} />
          <Info label="Ngày ký" value={formatDate(doc.signed_at)} />
          <Info label="ML-DSA key ref" value={doc.public_key_ref || "-"} breakText />
          <Info label="QR key ref (Ed25519)" value={doc.qr_public_key_ref || "-"} breakText />
          <Info label="Người ký" value={doc.signer_email || doc.signed_by || "-"} />
        </div>

        {(isRejected || doc.review_note) && (
          <p style={isRejected ? styles.rejectNote : styles.note}>
            {isRejected ? "Lý do từ chối: " : "Ghi chú duyệt: "}
            {doc.review_note || "(không có)"}
          </p>
        )}
      </section>

      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>Thao tác tài liệu</h2>

        <div style={styles.actions}>
          <button type="button" onClick={handleDownload} style={styles.btnBlue}>
            Tải PDF gốc
          </button>

          {isSigner && isApproved && (
            <button
              type="button"
              onClick={handleSign}
              disabled={signing}
              style={styles.btnGreen}
            >
              {signing ? "Đang ký..." : "Ký ML-DSA-44"}
            </button>
          )}

          {isSigned && (
            <>
              <button
                type="button"
                onClick={handleDownloadSigned}
                style={styles.btnGreen}
              >
                Tải PDF đã ký (QR + chữ ký)
              </button>

              <button
                type="button"
                onClick={handleShowQr}
                disabled={qrLoading}
                style={styles.btnOutline}
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

        {isReviewer && isPendingReview && (
          <div style={styles.reviewBox}>
            <p style={styles.reviewTitle}>Duyệt hồ sơ</p>
            <textarea
              value={reviewNote}
              onChange={(e) => setReviewNote(e.target.value)}
              placeholder="Ghi chú duyệt / lý do từ chối..."
              style={styles.textarea}
            />
            <div style={styles.actions}>
              <button
                type="button"
                onClick={handleApprove}
                disabled={reviewing}
                style={styles.btnGreen}
              >
                {reviewing ? "..." : "Phê duyệt"}
              </button>
              <button
                type="button"
                onClick={handleReject}
                disabled={reviewing}
                style={styles.btnRed}
              >
                Từ chối
              </button>
            </div>
          </div>
        )}

        {isPendingReview && !isReviewer && (
          <p style={styles.note}>Tài liệu đang chờ người duyệt phê duyệt.</p>
        )}
        {isApproved && !isSigner && (
          <p style={styles.note}>Đã duyệt — đang chờ người ký áp chữ ký ML-DSA-44.</p>
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
  badgeApproved: {
    background: "#dbeafe",
    color: "#1e40af",
  },
  badgeRejected: {
    background: "#fee2e2",
    color: "#991b1b",
  },
  reviewBox: {
    marginTop: 16,
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 12,
    padding: 14,
  },
  reviewTitle: {
    margin: "0 0 10px",
    fontWeight: 900,
    color: "#111827",
  },
  textarea: {
    width: "100%",
    minHeight: 64,
    padding: 10,
    borderRadius: 10,
    border: "1px solid #cbd5e1",
    fontFamily: "inherit",
    fontSize: 14,
    boxSizing: "border-box",
    marginBottom: 12,
  },
  btnRed: {
    background: "#b91c1c",
    color: "white",
    border: 0,
    borderRadius: 10,
    padding: "10px 14px",
    cursor: "pointer",
    fontWeight: 800,
  },
  rejectNote: {
    marginTop: 14,
    background: "#fef2f2",
    border: "1px solid #fecaca",
    color: "#991b1b",
    padding: "10px 12px",
    borderRadius: 10,
    fontWeight: 650,
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
