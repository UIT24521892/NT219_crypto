import { useEffect, useMemo, useState } from "react";
import Navbar from "../components/Navbar";
import UploadForm from "../components/UploadForm";
import DocumentTable from "../components/DocumentTable";
import { getDocumentsApi, uploadDocumentApi, getDownloadUrl } from "../services/documentService";

export default function CitizenPage() {
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

  const handleUpload = async (file) => {
    try {
      await uploadDocumentApi(file);
      alert("Tải hồ sơ thành công");
      await loadDocuments();
    } catch (error) {
      alert(error?.response?.data?.message || "Tải hồ sơ thất bại");
    }
  };

  const signedCount = useMemo(() => documents.filter((d) => d.status === "signed").length, [documents]);

  return (
    <div>
      <Navbar />
      <main className="shell page-stack">
        <section className="hero-panel citizen-hero">
          <div>
            <span className="hero-tag">Bảng điều khiển công dân</span>
            <h1>Theo dõi hồ sơ của bạn</h1>
            <p>Tải tài liệu mới, theo dõi trạng thái xử lý và kiểm tra tài liệu đã ký.</p>
          </div>
          <div className="stats-row">
            <div className="stat-card">
              <strong>{documents.length}</strong>
              <span>Tổng hồ sơ</span>
            </div>
            <div className="stat-card">
              <strong>{signedCount}</strong>
              <span>Đã ký</span>
            </div>
          </div>
        </section>

        <UploadForm onUpload={handleUpload} />

        <section className="section-gap">
          <div className="section-header">
            <div>
              <h3>Danh sách tài liệu</h3>
              <p>Xem nhanh trạng thái từng hồ sơ đã nộp.</p>
            </div>
          </div>
          <DocumentTable documents={documents} getDownloadUrl={getDownloadUrl} />
        </section>
      </main>
    </div>
  );
}
