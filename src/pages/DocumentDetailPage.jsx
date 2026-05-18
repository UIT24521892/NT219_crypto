import { useParams } from "react-router-dom";

export default function DocumentDetailPage() {
  const { id } = useParams();

  return (
    <main style={{ padding: 24 }}>
      <h1>Chi tiết tài liệu</h1>

      <p>Document ID: {id}</p>

      <div style={{ marginTop: 20 }}>
        <p>Thuật toán: FALCON-512</p>
        <p>SHA-256 hash: mock-sha256-hash</p>
        <p>Signature status: VALID</p>
      </div>
    </main>
  );
}