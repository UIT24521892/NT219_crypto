import { useState } from "react";

export default function UploadForm({ onUpload }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      alert("Chọn file trước");
      return;
    }

    setLoading(true);
    try {
      await onUpload(file);
      setFile(null);
      e.target.reset();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card section-gap">
      <div className="section-header">
        <div>
          <h3>Tải hồ sơ mới</h3>
          <p>Hỗ trợ PDF, DOC, DOCX, PNG, JPG.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="upload-form">
        <label className="file-picker">
          <input
            type="file"
            accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
            onChange={(e) => setFile(e.target.files[0])}
          />
          <span>{file ? file.name : "Chọn tệp từ máy tính"}</span>
        </label>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Đang tải..." : "Tải lên"}
        </button>
      </form>
    </div>
  );
}
