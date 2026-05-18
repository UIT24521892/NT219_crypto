import { useEffect, useState } from "react";
import {
  getDocuments,
  uploadDocument,
  signDocument,
} from "../services/documents";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");

  const loadDocuments = async () => {
    const data = await getDocuments();
    setDocuments(Array.isArray(data) ? data : data.documents || []);
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleUpload = async () => {
    if (!file) return setMessage("Chọn file trước đã");
    setMessage("Đang upload...");
    await uploadDocument(file);
    setMessage("Upload thành công");
    setFile(null);
    loadDocuments();
  };

  const handleSign = async (id) => {
    setMessage("Đang ký tài liệu...");
    await signDocument(id);
    setMessage("Ký tài liệu thành công");
    loadDocuments();
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Quản lý tài liệu</h1>

      <section style={{ marginBottom: 24 }}>
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button onClick={handleUpload}>Upload PDF</button>
      </section>

      {message && <p>{message}</p>}

      <table border="1" cellPadding="8" style={{ width: "100%" }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Tên file</th>
            <th>Hash</th>
            <th>Trạng thái</th>
            <th>Thao tác</th>
          </tr>
        </thead>

        <tbody>
          {documents.map((doc) => (
            <tr key={doc.id}>
              <td>{doc.id}</td>
              <td>{doc.fileName || doc.filename}</td>
              <td style={{ maxWidth: 240, wordBreak: "break-all" }}>
                {doc.documentHash || doc.fileHash || "-"}
              </td>
              <td>{doc.status || "-"}</td>
              <td>
                <button onClick={() => handleSign(doc.id)}>Ký</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}