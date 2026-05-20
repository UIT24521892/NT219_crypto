import React, { useEffect, useMemo, useRef, useState } from "react";
import { QRCodeCanvas } from "qrcode.react";
import "./App.css";

/**
 * App.clean.jsx
 * Frontend sạch cho đồ án xác thực tài liệu bằng chữ ký số hậu lượng tử + QR.
 *
 * Cách dùng:
 * 1. Copy file này đè lên src/App.jsx
 * 2. Giữ dependency hiện có: react, qrcode.react
 * 3. Chạy: npm run dev
 *
 * Khi chưa có backend:
 * - Để VITE_USE_MOCK=true trong .env.development
 *
 * Khi backend xong:
 * - Đặt VITE_USE_MOCK=false
 * - Đặt VITE_API_BASE_URL=http://localhost:8000/api
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
const USE_MOCK = String(import.meta.env.VITE_USE_MOCK ?? "true") === "true";
const STORAGE_KEY = "pq_document_verifier_state_v1";
const FALCON_ALGORITHM = "FALCON-512";

const DEFAULT_STATE = {
  users: [
    { id: 1, name: "Admin", email: "admin@demo.vn", password: "admin123", role: "ADMIN" },
    { id: 2, name: "Citizen", email: "citizen@demo.vn", password: "123456", role: "CITIZEN" },
  ],
  documents: [],
  auditLogs: [],
};

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : DEFAULT_STATE;
  } catch {
    return DEFAULT_STATE;
  }
}

function saveState(nextState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState));
}

function createId(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function nowIso() {
  return new Date().toISOString();
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("vi-VN");
}

function fileSize(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

async function sha256File(file) {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function createQrPayload(document) {
  return JSON.stringify({
    type: "PQ_DOCUMENT_SIGNATURE",
    version: 1,
    documentId: document.id,
    fileName: document.fileName,
    documentHash: document.documentHash,
    signature: document.signature,
    algorithm: document.algorithm,
    signedAt: document.signedAt,
  });
}

function parseQrPayload(text) {
  try {
    const data = JSON.parse(text);
    if (data?.type !== "PQ_DOCUMENT_SIGNATURE") {
      throw new Error("QR không đúng định dạng của hệ thống.");
    }
    return data;
  } catch (error) {
    throw new Error(error.message || "Không đọc được dữ liệu QR.");
  }
}

function addAuditLog(state, action, actor, detail) {
  return {
    ...state,
    auditLogs: [
      {
        id: createId("log"),
        action,
        actor: actor?.email || "anonymous",
        detail,
        createdAt: nowIso(),
      },
      ...state.auditLogs,
    ],
  };
}

async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("accessToken");
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API error ${response.status}`);
  }

  return response.json();
}

const realApi = {
  login: (email, password) =>
    apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  listDocuments: () => apiRequest("/documents"),

  uploadDocument: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest("/documents/upload", { method: "POST", body: formData });
  },

  signDocument: (documentId) =>
    apiRequest(`/documents/${documentId}/sign`, {
      method: "POST",
    }),

  verifyQr: (payload) =>
    apiRequest("/verify", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  auditLogs: () => apiRequest("/audit-logs"),
};

const mockApi = {
  async login(email, password) {
    const state = loadState();
    const user = state.users.find((item) => item.email === email && item.password === password);
    if (!user) throw new Error("Sai email hoặc mật khẩu.");
    const safeUser = { id: user.id, name: user.name, email: user.email, role: user.role };
    localStorage.setItem("accessToken", `mock-token-${user.id}`);
    localStorage.setItem("currentUser", JSON.stringify(safeUser));
    saveState(addAuditLog(state, "LOGIN", safeUser, "User logged in"));
    return { user: safeUser, accessToken: `mock-token-${user.id}` };
  },

  async listDocuments() {
    return loadState().documents;
  },

  async uploadDocument(file, user) {
    const state = loadState();
    const documentHash = await sha256File(file);
    const document = {
      id: createId("doc"),
      fileName: file.name,
      fileType: file.type || "application/octet-stream",
      fileSize: file.size,
      documentHash,
      status: "UPLOADED",
      algorithm: null,
      signature: null,
      signedAt: null,
      uploadedBy: user?.email || "unknown",
      uploadedAt: nowIso(),
    };

    const nextState = addAuditLog(
      { ...state, documents: [document, ...state.documents] },
      "UPLOAD_DOCUMENT",
      user,
      `Uploaded ${file.name}`
    );
    saveState(nextState);
    return document;
  },

  async signDocument(documentId, user) {
    const state = loadState();
    const document = state.documents.find((item) => item.id === documentId);
    if (!document) throw new Error("Không tìm thấy tài liệu.");

    const signedAt = nowIso();
    const signatureSource = `${document.documentHash}.${FALCON_ALGORITHM}.${signedAt}`;
    const fakeSignature = btoa(signatureSource).replaceAll("=", "");

    const signedDocument = {
      ...document,
      status: "SIGNED",
      algorithm: FALCON_ALGORITHM,
      signature: fakeSignature,
      signedAt,
      signedBy: user?.email || "admin",
    };

    const nextState = addAuditLog(
      {
        ...state,
        documents: state.documents.map((item) => (item.id === documentId ? signedDocument : item)),
      },
      "SIGN_DOCUMENT",
      user,
      `Signed ${document.fileName} with ${FALCON_ALGORITHM}`
    );
    saveState(nextState);
    return signedDocument;
  },

  async verifyQr(payload, user) {
    const state = loadState();
    const document = state.documents.find((item) => item.id === payload.documentId);
    const valid = Boolean(
      document &&
        document.status === "SIGNED" &&
        document.documentHash === payload.documentHash &&
        document.signature === payload.signature &&
        document.algorithm === payload.algorithm
    );

    saveState(
      addAuditLog(
        state,
        "VERIFY_QR",
        user,
        `${valid ? "Valid" : "Invalid"} verification for ${payload.fileName || payload.documentId}`
      )
    );

    return {
      valid,
      message: valid ? "Tài liệu hợp lệ, chữ ký đúng." : "Tài liệu không hợp lệ hoặc dữ liệu QR bị sai.",
      document: document || null,
      checkedAt: nowIso(),
    };
  },

  async auditLogs() {
    return loadState().auditLogs;
  },
};

const api = USE_MOCK ? mockApi : realApi;

export default function App() {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("currentUser"));
    } catch {
      return null;
    }
  });
  const [page, setPage] = useState("dashboard");
  const [documents, setDocuments] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function refreshData() {
    if (!user) return;
    const [docs, logs] = await Promise.all([api.listDocuments(), api.auditLogs()]);
    setDocuments(docs);
    setAuditLogs(logs);
  }

  useEffect(() => {
    refreshData().catch((error) => setMessage(error.message));
  }, [user]);

  function logout() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("currentUser");
    setUser(null);
    setDocuments([]);
    setAuditLogs([]);
    setPage("dashboard");
  }

  async function handleLogin(email, password) {
    setLoading(true);
    setMessage("");
    try {
      const result = await api.login(email, password);
      localStorage.setItem("accessToken", result.accessToken || "token");
      localStorage.setItem("currentUser", JSON.stringify(result.user));
      setUser(result.user);
      setPage("dashboard");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(file) {
    setLoading(true);
    setMessage("");
    try {
      await api.uploadDocument(file, user);
      await refreshData();
      setMessage("Upload tài liệu thành công.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSign(documentId) {
    setLoading(true);
    setMessage("");
    try {
      const signedDocument = await api.signDocument(documentId, user);
      await refreshData();
      setSelectedDocument(signedDocument);
      setPage("qr");
      setMessage("Ký số thành công, QR đã được tạo.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(rawText) {
    setLoading(true);
    setMessage("");
    try {
      const payload = parseQrPayload(rawText);
      const result = await api.verifyQr(payload, user);
      await refreshData();
      return result;
    } catch (error) {
      return {
        valid: false,
        message: error.message,
        checkedAt: nowIso(),
      };
    } finally {
      setLoading(false);
    }
  }

  if (!user) {
    return (
      <Shell message={message} loading={loading}>
        <LoginPage onLogin={handleLogin} loading={loading} />
      </Shell>
    );
  }

  return (
    <Shell message={message} loading={loading}>
      <Header user={user} page={page} onNavigate={setPage} onLogout={logout} />

      {page === "dashboard" && (
        <DashboardPage
          user={user}
          documents={documents}
          onUpload={handleUpload}
          onSign={handleSign}
          onOpenQr={(document) => {
            setSelectedDocument(document);
            setPage("qr");
          }}
        />
      )}

      {page === "qr" && <QrPage document={selectedDocument} />}

      {page === "verify" && <VerifyPage onVerify={handleVerify} />}

      {page === "logs" && <AuditLogPage logs={auditLogs} />}
    </Shell>
  );
}

function Shell({ children, message, loading }) {
  return (
    <main style={styles.app}>
      <section style={styles.container}>
        {loading && <div style={styles.notice}>Đang xử lý...</div>}
        {message && <div style={styles.notice}>{message}</div>}
        {children}
      </section>
    </main>
  );
}

function Header({ user, page, onNavigate, onLogout }) {
  return (
    <header style={styles.header}>
      <div>
        <h1 style={styles.title}>PQ Document Verifier</h1>
        <p style={styles.subtitle}>Xác thực tài liệu bằng chữ ký số hậu lượng tử và QR</p>
      </div>
      <nav style={styles.nav}>
        <button style={buttonStyle(page === "dashboard")} onClick={() => onNavigate("dashboard")}>Dashboard</button>
        <button style={buttonStyle(page === "verify")} onClick={() => onNavigate("verify")}>Verify QR</button>
        <button style={buttonStyle(page === "logs")} onClick={() => onNavigate("logs")}>Audit log</button>
        <span style={styles.userBadge}>{user.name} · {user.role}</span>
        <button style={styles.secondaryButton} onClick={onLogout}>Đăng xuất</button>
      </nav>
    </header>
  );
}

function LoginPage({ onLogin, loading }) {
  const [email, setEmail] = useState("admin@demo.vn");
  const [password, setPassword] = useState("admin123");

  return (
    <section style={styles.cardNarrow}>
      <h1 style={styles.title}>Đăng nhập</h1>
      <p style={styles.subtitle}>Mock account: admin@demo.vn/admin123 hoặc citizen@demo.vn/123456</p>
      <form
        style={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          onLogin(email, password);
        }}
      >
        <label style={styles.label}>Email</label>
        <input style={styles.input} value={email} onChange={(event) => setEmail(event.target.value)} />
        <label style={styles.label}>Mật khẩu</label>
        <input
          style={styles.input}
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <button style={styles.primaryButton} disabled={loading}>Đăng nhập</button>
      </form>
    </section>
  );
}

function DashboardPage({ user, documents, onUpload, onSign, onOpenQr }) {
  const signedCount = documents.filter((item) => item.status === "SIGNED").length;

  return (
    <section style={styles.grid}>
      <div style={styles.card}>
        <h2>Quy trình hệ thống</h2>
        <ol style={styles.flowList}>
          <li>Upload file thật</li>
          <li>Hash SHA-256 từ nội dung file</li>
          <li>Ký hash bằng {FALCON_ALGORITHM}</li>
          <li>Sinh QR chứa hash + signature</li>
          <li>Scan QR để verify chữ ký</li>
        </ol>
      </div>

      <div style={styles.card}>
        <h2>Thống kê</h2>
        <p>Tổng tài liệu: <b>{documents.length}</b></p>
        <p>Đã ký: <b>{signedCount}</b></p>
        <p>Chưa ký: <b>{documents.length - signedCount}</b></p>
      </div>

      <div style={styles.cardWide}>
        <h2>Upload tài liệu</h2>
        <UploadBox onUpload={onUpload} disabled={user.role !== "ADMIN" && user.role !== "CITIZEN"} />
      </div>

      <div style={styles.cardWide}>
        <h2>Danh sách tài liệu</h2>
        <DocumentTable user={user} documents={documents} onSign={onSign} onOpenQr={onOpenQr} />
      </div>
    </section>
  );
}

function UploadBox({ onUpload, disabled }) {
  const [file, setFile] = useState(null);

  return (
    <form
      style={styles.uploadBox}
      onSubmit={(event) => {
        event.preventDefault();
        if (file) onUpload(file);
      }}
    >
      <input
        style={styles.input}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.doc,.docx"
        disabled={disabled}
        onChange={(event) => setFile(event.target.files?.[0] || null)}
      />
      <button style={styles.primaryButton} disabled={!file || disabled}>Upload</button>
    </form>
  );
}

function DocumentTable({ user, documents, onSign, onOpenQr }) {
  if (!documents.length) return <p>Chưa có tài liệu.</p>;

  return (
    <div style={styles.tableWrap}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th>Tên file</th>
            <th>Kích thước</th>
            <th>Trạng thái</th>
            <th>Hash SHA-256</th>
            <th>Thời gian</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((document) => (
            <tr key={document.id}>
              <td>{document.fileName}</td>
              <td>{fileSize(document.fileSize)}</td>
              <td><StatusBadge status={document.status} /></td>
              <td><code title={document.documentHash}>{document.documentHash.slice(0, 18)}...</code></td>
              <td>{formatDate(document.uploadedAt)}</td>
              <td style={styles.actions}>
                {document.status !== "SIGNED" && user.role === "ADMIN" && (
                  <button style={styles.primaryButtonSmall} onClick={() => onSign(document.id)}>Ký số</button>
                )}
                {document.status === "SIGNED" && (
                  <button style={styles.secondaryButtonSmall} onClick={() => onOpenQr(document)}>Xem QR</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ status }) {
  const signed = status === "SIGNED";
  return <span style={signed ? styles.badgeSuccess : styles.badgeWarning}>{signed ? "Đã ký" : "Chưa ký"}</span>;
}

function QrPage({ document }) {
  const qrText = useMemo(() => (document?.signature ? createQrPayload(document) : ""), [document]);

  if (!document) {
    return <section style={styles.card}><p>Chọn một tài liệu đã ký để xem QR.</p></section>;
  }

  if (document.status !== "SIGNED") {
    return <section style={styles.card}><p>Tài liệu này chưa được ký số.</p></section>;
  }

  return (
    <section style={styles.cardWideCenter}>
      <h2>QR xác thực tài liệu</h2>
      <p><b>{document.fileName}</b></p>
      <QRCodeCanvas value={qrText} size={260} includeMargin />
      <div style={styles.qrPayload}>
        <p><b>Payload QR</b></p>
        <pre>{JSON.stringify(JSON.parse(qrText), null, 2)}</pre>
      </div>
    </section>
  );
}

function VerifyPage({ onVerify }) {
  const [manualText, setManualText] = useState("");
  const [result, setResult] = useState(null);
  const [cameraError, setCameraError] = useState("");
  const [isScanning, setIsScanning] = useState(false);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);

  async function verify(text) {
    const nextResult = await onVerify(text);
    setResult(nextResult);
    return nextResult;
  }

  async function startCameraScan() {
    setCameraError("");
    setIsScanning(true);

    try {
      if (!("BarcodeDetector" in window)) {
        throw new Error("Trình duyệt này chưa hỗ trợ BarcodeDetector. Dán payload QR vào ô bên dưới để verify.");
      }

      const detector = new window.BarcodeDetector({ formats: ["qr_code"] });
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      await videoRef.current.play();

      timerRef.current = window.setInterval(async () => {
        if (!videoRef.current) return;
        const codes = await detector.detect(videoRef.current);
        if (codes.length > 0) {
          stopCameraScan();
          const rawValue = codes[0].rawValue;
          setManualText(rawValue);
          verify(rawValue);
        }
      }, 700);
    } catch (error) {
      setCameraError(error.message);
      setIsScanning(false);
    }
  }

  function stopCameraScan() {
    setIsScanning(false);
    if (timerRef.current) window.clearInterval(timerRef.current);
    if (streamRef.current) streamRef.current.getTracks().forEach((track) => track.stop());
    timerRef.current = null;
    streamRef.current = null;
  }

  useEffect(() => stopCameraScan, []);

  return (
    <section style={styles.cardWide}>
      <h2>Verify QR</h2>
      <p>Scan QR hoặc dán payload QR để kiểm tra chữ ký số.</p>

      <div style={styles.verifyGrid}>
        <div>
          <video ref={videoRef} style={styles.video} muted playsInline />
          <div style={styles.actions}>
            {!isScanning ? (
              <button style={styles.primaryButtonSmall} onClick={startCameraScan}>Bật camera scan</button>
            ) : (
              <button style={styles.secondaryButtonSmall} onClick={stopCameraScan}>Tắt camera</button>
            )}
          </div>
          {cameraError && <p style={styles.error}>{cameraError}</p>}
        </div>

        <form
          style={styles.form}
          onSubmit={(event) => {
            event.preventDefault();
            verify(manualText);
          }}
        >
          <label style={styles.label}>QR payload</label>
          <textarea
            style={styles.textarea}
            value={manualText}
            onChange={(event) => setManualText(event.target.value)}
            placeholder='Dán JSON trong QR vào đây nếu camera không scan được'
          />
          <button style={styles.primaryButton} disabled={!manualText.trim()}>Verify</button>
        </form>
      </div>

      {result && (
        <div style={result.valid ? styles.resultValid : styles.resultInvalid}>
          <h3>{result.valid ? "VALID" : "INVALID"}</h3>
          <p>{result.message}</p>
          <p>Kiểm tra lúc: {formatDate(result.checkedAt)}</p>
        </div>
      )}
    </section>
  );
}

function AuditLogPage({ logs }) {
  return (
    <section style={styles.cardWide}>
      <h2>Audit log</h2>
      {!logs.length ? (
        <p>Chưa có log.</p>
      ) : (
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th>Action</th>
                <th>Actor</th>
                <th>Detail</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{log.action}</td>
                  <td>{log.actor}</td>
                  <td>{log.detail}</td>
                  <td>{formatDate(log.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function buttonStyle(active) {
  return active ? styles.primaryButtonSmall : styles.secondaryButtonSmall;
}

const styles = {
  app: {
    minHeight: "100vh",
    background: "#f5f7fb",
    color: "#111827",
    fontFamily: "Inter, system-ui, Arial, sans-serif",
    padding: 24,
  },
  container: {
    maxWidth: 1180,
    margin: "0 auto",
  },
  header: {
    background: "white",
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    boxShadow: "0 8px 30px rgba(15, 23, 42, 0.08)",
    display: "flex",
    justifyContent: "space-between",
    gap: 16,
    flexWrap: "wrap",
  },
  title: { margin: 0, fontSize: 28 },
  subtitle: { margin: "6px 0 0", color: "#6b7280" },
  nav: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" },
  userBadge: { padding: "8px 10px", background: "#eef2ff", borderRadius: 10, fontSize: 13 },
  notice: {
    background: "#fff7ed",
    border: "1px solid #fed7aa",
    padding: 12,
    borderRadius: 12,
    marginBottom: 12,
  },
  grid: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16 },
  card: {
    background: "white",
    borderRadius: 16,
    padding: 20,
    boxShadow: "0 8px 30px rgba(15, 23, 42, 0.08)",
  },
  cardNarrow: {
    maxWidth: 440,
    margin: "80px auto",
    background: "white",
    borderRadius: 16,
    padding: 24,
    boxShadow: "0 8px 30px rgba(15, 23, 42, 0.08)",
  },
  cardWide: {
    gridColumn: "1 / -1",
    background: "white",
    borderRadius: 16,
    padding: 20,
    boxShadow: "0 8px 30px rgba(15, 23, 42, 0.08)",
  },
  cardWideCenter: {
    background: "white",
    borderRadius: 16,
    padding: 24,
    textAlign: "center",
    boxShadow: "0 8px 30px rgba(15, 23, 42, 0.08)",
  },
  form: { display: "flex", flexDirection: "column", gap: 10 },
  label: { fontWeight: 700 },
  input: { padding: 12, borderRadius: 10, border: "1px solid #d1d5db" },
  textarea: { padding: 12, borderRadius: 10, border: "1px solid #d1d5db", minHeight: 160 },
  primaryButton: {
    border: 0,
    borderRadius: 10,
    padding: "12px 16px",
    background: "#2563eb",
    color: "white",
    fontWeight: 700,
    cursor: "pointer",
  },
  secondaryButton: {
    border: "1px solid #d1d5db",
    borderRadius: 10,
    padding: "12px 16px",
    background: "white",
    color: "#111827",
    fontWeight: 700,
    cursor: "pointer",
  },
  primaryButtonSmall: {
    border: 0,
    borderRadius: 9,
    padding: "8px 10px",
    background: "#2563eb",
    color: "white",
    fontWeight: 700,
    cursor: "pointer",
  },
  secondaryButtonSmall: {
    border: "1px solid #d1d5db",
    borderRadius: 9,
    padding: "8px 10px",
    background: "white",
    color: "#111827",
    fontWeight: 700,
    cursor: "pointer",
  },
  uploadBox: { display: "flex", gap: 10, flexWrap: "wrap" },
  flowList: { lineHeight: 1.8 },
  tableWrap: { overflowX: "auto" },
  table: { width: "100%", borderCollapse: "collapse" },
  actions: { display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" },
  badgeSuccess: { background: "#dcfce7", color: "#166534", padding: "5px 8px", borderRadius: 999, fontWeight: 700 },
  badgeWarning: { background: "#fef3c7", color: "#92400e", padding: "5px 8px", borderRadius: 999, fontWeight: 700 },
  qrPayload: { textAlign: "left", marginTop: 20, background: "#f9fafb", padding: 12, borderRadius: 12, overflowX: "auto" },
  verifyGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 },
  video: { width: "100%", minHeight: 260, background: "#111827", borderRadius: 12 },
  resultValid: { marginTop: 16, padding: 16, borderRadius: 12, background: "#dcfce7", color: "#166534" },
  resultInvalid: { marginTop: 16, padding: 16, borderRadius: 12, background: "#fee2e2", color: "#991b1b" },
  error: { color: "#991b1b" },
};
