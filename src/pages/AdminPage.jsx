import { useState } from "react";
import {
  uploadDocument,
  signDocument,
} from "../services/documents";

export default function AdminPage() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");

  const handleUpload = async () => {
    if (!file) return;

    setMessage("Đang upload...");
    await uploadDocument(file);

    setMessage("Upload thành công");
  };

  const handleSign = async () => {
    setMessage("Đang ký bằng FALCON...");
    await signDocument(1);

    setMessage("Ký tài liệu thành công");
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Admin Dashboard</h1>

      <div style={{ marginTop: 20 }}>
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => setFile(e.target.files[0])}
        />

        <button onClick={handleUpload}>
          Upload PDF
        </button>

        <button onClick={handleSign}>
          Ký tài liệu
        </button>
      </div>

      <p>{message}</p>
    </main>
  );
}