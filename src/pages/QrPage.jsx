import { useLocation } from "react-router-dom";
import { QRCodeCanvas } from "qrcode.react";
import Navbar from "../components/Navbar";

export default function QrPage() {
  const location = useLocation();
  const doc = location.state?.doc;

  return (
    <div>
      <Navbar />
      <main className="shell page-stack">
        <section className="hero-panel qr-hero">
          <div>
            <span className="hero-tag">Mã xác thực</span>
            <h1>Chi tiết QR tài liệu</h1>
            <p>Hiển thị mã QR và dữ liệu đã ký cho tài liệu đã xử lý.</p>
          </div>
        </section>

        {!doc ? (
          <div className="card"><p>Không có dữ liệu QR.</p></div>
        ) : (
          <div className="qr-layout">
            <div className="card qr-card center-card">
              <QRCodeCanvas value={doc.qrCodeData || "No QR data"} size={220} />
              <div className="qr-caption">Quét mã để xác minh tài liệu</div>
            </div>

            <div className="card detail-card">
              <h3>Thông tin tài liệu</h3>
              <div className="detail-grid">
                <div><strong>Mã tài liệu</strong><span>#{doc.id}</span></div>
                <div><strong>Tên tệp</strong><span>{doc.fileName}</span></div>
                <div><strong>Trạng thái</strong><span>{doc.status}</span></div>
              </div>
              <pre className="code-box">{doc.qrCodeData}</pre>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
