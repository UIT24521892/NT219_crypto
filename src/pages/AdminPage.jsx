import { useEffect, useMemo, useState } from "react";
import Navbar from "../components/Navbar";
import DocumentTable from "../components/DocumentTable";
import { getDocumentsApi, signDocumentApi, getDownloadUrl } from "../services/documentService";

export default function AdminPage() {
  const [documents, setDocuments] = useState([]);

  const loadDocuments = async () => {
    try {
      const data = await getDocumentsApi();
      setDocuments(data);
    } catch (error) {
      alert("Không tải được danh sách tài liệu");
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleSign = async (doc) => {
    try {
      const payload = {
        signature: `mock-signature-for-doc-${doc.id}`,
        documentHash: `mock-hash-for-doc-${doc.id}`,
        qrCodeData: JSON.stringify(
          {
            documentId: doc.id,
            fileName: doc.fileName,
            status: "signed",
            signedAt: new Date().toISOString(),
          },
          null,
          2
        ),
      };

      const res = await signDocumentApi(doc.id, payload);
      if (res.success) {
        alert(res.message);
        await loadDocuments();
      } else {
        alert(res.message || "Ký tài liệu thất bại");
      }
    } catch (error) {
      alert(error?.response?.data?.message || "Ký tài liệu thất bại");
    }
  };

  const pendingCount = useMemo(() => documents.filter((d) => d.status === "pending").length, [documents]);
  const signedCount = useMemo(() => documents.filter((d) => d.status === "signed").length, [documents]);

  return (
    <div>
      <Navbar />
      <main className="shell page-stack">
        <section className="hero-panel admin-hero">
          <div>
            <span className="hero-tag">Bảng điều khiển quản trị</span>
            <h1>Xử lý hồ sơ điện tử</h1>
            <p>Kiểm tra tài liệu, ký số mô phỏng và xác minh QR cho từng hồ sơ.</p>
          </div>
          <div className="stats-row">
            <div className="stat-card">
              <strong>{documents.length}</strong>
              <span>Tổng hồ sơ</span>
            </div>
            <div className="stat-card warning">
              <strong>{pendingCount}</strong>
              <span>Chờ ký</span>
            </div>
            <div className="stat-card success">
              <strong>{signedCount}</strong>
              <span>Đã ký</span>
            </div>
          </div>
        </section>

        <section className="section-gap">
          <div className="section-header">
            <div>
              <h3>Danh sách hồ sơ</h3>
              <p>Thực hiện ký số hoặc mở mã QR cho tài liệu đã xử lý.</p>
            </div>
          </div>
          <DocumentTable
            documents={documents}
            isAdmin
            onSign={handleSign}
            getDownloadUrl={getDownloadUrl}
          />
        </section>
      </main>
    </div>
  );
}
