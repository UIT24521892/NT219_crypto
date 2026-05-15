export const formatDate = (value) => {
  if (!value) return "-";
  return new Date(value).toLocaleString("vi-VN");
};

export const formatFileSize = (bytes) => {
  if (!bytes && bytes !== 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const getStatusLabel = (status) => {
  const map = {
    pending: "Chờ ký",
    signed: "Đã ký",
    rejected: "Từ chối",
  };
  return map[status] || status;
};

export const getFileTypeLabel = (type) => {
  if (!type) return "-";
  if (type.includes("pdf")) return "PDF";
  if (type.includes("word") || type.includes("doc")) return "DOC";
  if (type.includes("png")) return "PNG";
  if (type.includes("jpeg") || type.includes("jpg")) return "JPG";
  return type;
};
