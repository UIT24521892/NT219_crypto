import { useCallback, useEffect, useState } from "react";

import { listAgencies, assignAgency } from "../services/agencies";

export default function AgenciesPage() {
  const [agencies, setAgencies] = useState([]);
  const [email, setEmail] = useState("");
  const [agencyCode, setAgencyCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("info");

  const load = useCallback(async () => {
    try {
      const data = await listAgencies();
      const list = Array.isArray(data) ? data : [];
      setAgencies(list);
      if (list.length && !agencyCode) setAgencyCode(list[0].code);
    } catch (err) {
      setMessageType("error");
      setMessage(err.response?.data?.detail || "Không tải được danh sách cơ quan.");
    }
  }, [agencyCode]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function handleAssign(event) {
    event.preventDefault();
    const userEmail = email.trim();
    if (!userEmail) {
      setMessageType("error");
      setMessage("Nhập email người ký cần gán.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await assignAgency(userEmail, agencyCode);
      setMessageType("success");
      const label = agencyCode
        ? agencies.find((a) => a.code === agencyCode)?.name || agencyCode
        : "(bỏ gán)";
      setMessage(`Đã gán ${userEmail} → ${label}.`);
      setEmail("");
    } catch (err) {
      setMessageType("error");
      setMessage(err.response?.data?.detail || "Gán cơ quan thất bại.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <p style={styles.kicker}>Admin</p>
      <h1 style={styles.title}>Quản lý cơ quan nhà nước</h1>
      <p style={styles.subtitle}>
        Mỗi người ký hành động nhân danh một cơ quan. Tên cơ quan được ghi vào tài
        liệu và ràng buộc mật mã trong QR + chữ ký.
      </p>

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

      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>Gán cơ quan cho người ký</h2>
        <form onSubmit={handleAssign} style={styles.form}>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email người ký (signer)..."
            style={styles.input}
          />
          <select
            value={agencyCode}
            onChange={(e) => setAgencyCode(e.target.value)}
            style={styles.select}
          >
            <option value="">— Bỏ gán —</option>
            {agencies.map((a) => (
              <option key={a.code} value={a.code}>
                {a.name} ({a.code})
              </option>
            ))}
          </select>
          <button type="submit" disabled={busy} style={styles.btn}>
            {busy ? "..." : "Gán"}
          </button>
        </form>
      </section>

      <section style={styles.card}>
        <h2 style={styles.sectionTitle}>Danh sách cơ quan</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Mã</th>
              <th style={styles.th}>Tên cơ quan</th>
              <th style={styles.th}>Cấp</th>
            </tr>
          </thead>
          <tbody>
            {agencies.length === 0 ? (
              <tr>
                <td colSpan="3" style={styles.empty}>Chưa có cơ quan nào.</td>
              </tr>
            ) : (
              agencies.map((a) => (
                <tr key={a.code}>
                  <td style={styles.td}><code>{a.code}</code></td>
                  <td style={styles.td}>{a.name}</td>
                  <td style={styles.td}>{a.level}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}

const styles = {
  kicker: { margin: 0, color: "#8b1e1e", fontWeight: 900, textTransform: "uppercase", letterSpacing: 0.8, fontSize: 12 },
  title: { margin: "4px 0 0", fontSize: 30, color: "#111827" },
  subtitle: { color: "#64748b", marginTop: 6, marginBottom: 18 },
  card: { background: "white", border: "1px solid #e2e8f0", borderRadius: 14, padding: 18, marginBottom: 16 },
  sectionTitle: { margin: "0 0 14px", fontSize: 18, color: "#111827" },
  form: { display: "flex", gap: 10, flexWrap: "wrap" },
  input: { flex: "1 1 240px", padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", fontSize: 14 },
  select: { padding: "10px 12px", borderRadius: 10, border: "1px solid #cbd5e1", fontSize: 14 },
  btn: { background: "#8b1e1e", color: "white", border: 0, borderRadius: 10, padding: "10px 18px", fontWeight: 800, cursor: "pointer" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", padding: "8px 10px", borderBottom: "2px solid #e2e8f0", color: "#64748b", fontSize: 12, textTransform: "uppercase" },
  td: { padding: "8px 10px", borderBottom: "1px solid #f1f5f9" },
  empty: { padding: 18, textAlign: "center", color: "#64748b" },
  message: { padding: "12px 14px", borderRadius: 12, background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe", fontWeight: 650, marginBottom: 14 },
  msgOk: { background: "#ecfdf5", color: "#047857", borderColor: "#a7f3d0" },
  msgErr: { background: "#fef2f2", color: "#b91c1c", borderColor: "#fecaca" },
};
