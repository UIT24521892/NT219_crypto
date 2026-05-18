/**
 * VerifyPage — trang xác minh public.
 *
 * Đây là trang QR code trỏ về sau khi scan. URL có dạng:
 *   http://localhost:5173/verify?d=<doc_id>
 *
 * Khi điện thoại quét QR → mở browser → vào trang này → nó tự đọc
 * query param `d`, gọi GET /verify?d=<doc_id> backend, hiển thị kết quả.
 *
 * KHÔNG cần auth — đây là endpoint public để bất kỳ ai cũng verify được.
 *
 * Mô hình verify QUAN TRỌNG:
 *   - Backend của Trung dùng FALCON-512 thật để verify (server-side).
 *   - QR chỉ chứa URL ngắn, KHÔNG chứa signature.
 *   - Trang này không tự verify cryptography client-side — chỉ hiển thị kết quả backend trả.
 */
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { verifyDocument } from "../services/verify";

export default function VerifyPage() {
  const [searchParams] = useSearchParams();
  const docId = searchParams.get("d");

  const [state, setState] = useState({ status: "loading", data: null, error: null });

  useEffect(() => {
    if (!docId) {
      setState({ status: "error", error: "Thiếu mã tài liệu trong URL", data: null });
      return;
    }

    verifyDocument(docId)
      .then((data) => setState({ status: "done", data, error: null }))
      .catch((err) => {
        const msg =
          err.response?.status === 404
            ? "Không tìm thấy tài liệu"
            : err.response?.data?.detail || "Lỗi kết nối backend";
        setState({ status: "error", error: msg, data: null });
      });
  }, [docId]);

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.brand}>Citizen Services Portal</h1>
        <p style={styles.brandSubtitle}>Hệ thống xác thực tài liệu hậu lượng tử</p>

        {state.status === "loading" && (
          <p style={styles.loading}>Đang kiểm tra chữ ký...</p>
        )}

        {state.status === "error" && (
          <div style={styles.errorBox}>
            <h2 style={styles.errorTitle}>❌ Không thể xác minh</h2>
            <p>{state.error}</p>
          </div>
        )}

        {state.status === "done" && state.data && (
          <VerifyResult data={state.data} />
        )}
      </div>
    </div>
  );
}

function VerifyResult({ data }) {
  if (data.valid) {
    return (
      <div style={styles.validBox}>
        <h2 style={styles.validTitle}>✅ Tài liệu hợp lệ</h2>
        <p style={styles.validMessage}>
          Chữ ký FALCON-512 được xác minh thành công. Tài liệu chưa bị chỉnh sửa.
        </p>
        <DocumentInfo data={data} />
      </div>
    );
  }

  return (
    <div style={styles.invalidBox}>
      <h2 style={styles.invalidTitle}>⚠️ Tài liệu KHÔNG hợp lệ</h2>
      <p style={styles.invalidMessage}>{data.reason || "Chữ ký không khớp"}</p>
      <DocumentInfo data={data} />
    </div>
  );
}

function DocumentInfo({ data }) {
  return (
    <dl style={styles.info}>
      <Row label="Tên file" value={data.filename} />
      <Row label="Mã tài liệu" value={data.doc_id} mono />
      <Row
        label="SHA-256"
        value={`${data.file_hash.slice(0, 16)}...${data.file_hash.slice(-8)}`}
        mono
        title={data.file_hash}
      />
      <Row label="Kích thước" value={`${data.file_size} bytes`} />
      <Row label="Trạng thái" value={data.status} />
      {data.signed_at && (
        <Row
          label="Ký lúc"
          value={new Date(data.signed_at).toLocaleString("vi-VN")}
        />
      )}
      {data.signer_email && <Row label="Người ký" value={data.signer_email} />}
      {data.public_key_ref && (
        <Row label="Khoá công khai (ref)" value={data.public_key_ref} mono />
      )}
    </dl>
  );
}

function Row({ label, value, mono = false, title }) {
  return (
    <>
      <dt style={styles.dt}>{label}</dt>
      <dd
        style={{ ...styles.dd, fontFamily: mono ? "monospace" : "inherit" }}
        title={title}
      >
        {value}
      </dd>
    </>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "#f5f7fb",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  card: {
    width: "100%",
    maxWidth: 560,
    background: "white",
    borderRadius: 12,
    padding: 32,
    boxShadow: "0 8px 30px rgba(15,23,42,0.08)",
  },
  brand: { margin: "0 0 4px", color: "#1e3a8a", fontSize: 22 },
  brandSubtitle: { margin: "0 0 24px", color: "#6b7280", fontSize: 14 },
  loading: { textAlign: "center", color: "#6b7280", padding: 40 },
  validBox: {
    background: "#dcfce7",
    border: "1px solid #86efac",
    borderRadius: 8,
    padding: 20,
  },
  validTitle: { margin: "0 0 8px", color: "#166534", fontSize: 20 },
  validMessage: { margin: "0 0 16px", color: "#166534" },
  invalidBox: {
    background: "#fee2e2",
    border: "1px solid #fca5a5",
    borderRadius: 8,
    padding: 20,
  },
  invalidTitle: { margin: "0 0 8px", color: "#991b1b", fontSize: 20 },
  invalidMessage: { margin: "0 0 16px", color: "#991b1b" },
  errorBox: {
    background: "#fef3c7",
    border: "1px solid #fcd34d",
    borderRadius: 8,
    padding: 20,
  },
  errorTitle: { margin: "0 0 8px", color: "#92400e", fontSize: 20 },
  info: {
    display: "grid",
    gridTemplateColumns: "max-content 1fr",
    gap: "8px 16px",
    margin: 0,
    fontSize: 14,
  },
  dt: { color: "#475569", fontWeight: 500 },
  dd: { margin: 0, color: "#0f172a", wordBreak: "break-all" },
};
