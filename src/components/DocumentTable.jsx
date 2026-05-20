import { Link } from "react-router-dom";
import {
  formatDate,
  formatFileSize,
  getFileTypeLabel,
  getStatusLabel,
} from "../utils/format";

export default function DocumentTable({
  documents,
  isAdmin = false,
  onSign,
  getDownloadUrl,
}) {
  return (
    <div className="card table-card">
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Mã</th>
              <th>Tên tệp</th>
              <th>Loại</th>
              <th>Kích cỡ</th>
              <th>Trạng thái</th>
              {isAdmin && <th>Người tải lên</th>}
              <th>Tải lên lúc</th>
              <th>Ký lúc</th>
              <th>QR</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {documents.length === 0 ? (
              <tr>
                <td className="empty-row" colSpan={isAdmin ? 10 : 9}>
                  Chưa có tài liệu nào.
                </td>
              </tr>
            ) : (
              documents.map((doc) => (
                <tr key={doc.id}>
                  <td>#{doc.id}</td>
                  <td>
                    <div className="file-name">{doc.fileName}</div>
                  </td>
                  <td>{getFileTypeLabel(doc.fileType)}</td>
                  <td>{formatFileSize(doc.fileSize)}</td>
                  <td>
                    <span className={`status-pill ${doc.status}`}>
                      {getStatusLabel(doc.status)}
                    </span>
                  </td>
                  {isAdmin && <td>{doc.uploadedBy}</td>}
                  <td>{formatDate(doc.uploadedAt)}</td>
                  <td>{formatDate(doc.signedAt)}</td>
                  <td>
                    {doc.qrCodeData ? (
                      <Link className="link-inline" to={`/qr/${doc.id}`} state={{ doc }}>
                        Xem QR
                      </Link>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td>
                    <div className="row-actions">
                      <a className="btn btn-ghost" href={getDownloadUrl(doc.id)} download={doc.fileName}>
                        Tải xuống
                      </a>

                      {isAdmin && doc.status !== "signed" && (
                        <button className="btn btn-primary" onClick={() => onSign(doc)}>
                          Ký số
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
