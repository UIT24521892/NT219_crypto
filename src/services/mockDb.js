const USERS_KEY = "mock_users";
const DOCS_KEY = "mock_docs";

const now = () => new Date().toISOString();

function read(key, fallback) {
  const raw = localStorage.getItem(key);
  return raw ? JSON.parse(raw) : fallback;
}

function write(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function initMockData() {
  if (!localStorage.getItem(USERS_KEY)) {
    write(USERS_KEY, [
      {
        id: 1,
        fullName: "Quản trị viên",
        email: "admin@demo.vn",
        password: "admin123",
        role: "admin",
      },
      {
        id: 2,
        fullName: "Nguyễn Văn A",
        email: "citizen@demo.vn",
        password: "123456",
        role: "citizen",
        citizenId: "079204001234",
        phoneNumber: "0901234567",
      },
    ]);
  }

  if (!localStorage.getItem(DOCS_KEY)) {
    write(DOCS_KEY, [
      {
        id: 1,
        fileName: "ho-so-cap-cccd.pdf",
        fileType: "application/pdf",
        fileSize: 245760,
        status: "pending",
        uploadedBy: "Nguyễn Văn A",
        uploadedByEmail: "citizen@demo.vn",
        uploadedAt: now(),
        signedAt: null,
        qrCodeData: null,
        fileContent: "Đây là file mock để test giao diện tải xuống.",
      },
    ]);
  }
}

export async function mockRegister(payload) {
  initMockData();
  const users = read(USERS_KEY, []);
  const exists = users.some((u) => u.email === payload.email);

  if (exists) {
    return { success: false, message: "Email đã tồn tại" };
  }

  users.push({
    id: users.length + 1,
    fullName: payload.fullName,
    email: payload.email,
    password: payload.password,
    citizenId: payload.citizenId,
    phoneNumber: payload.phoneNumber,
    role: "citizen",
  });

  write(USERS_KEY, users);
  return { success: true, message: "Đăng ký thành công" };
}

export async function mockLogin(payload) {
  initMockData();
  const users = read(USERS_KEY, []);
  const user = users.find(
    (u) => u.email === payload.email && u.password === payload.password
  );

  if (!user) {
    return { success: false, message: "Sai email hoặc mật khẩu" };
  }

  const safeUser = {
    id: user.id,
    fullName: user.fullName,
    email: user.email,
    role: user.role,
    citizenId: user.citizenId,
    phoneNumber: user.phoneNumber,
  };

  return {
    success: true,
    accessToken: `mock-token-${user.id}`,
    user: safeUser,
  };
}

export async function mockMe() {
  const raw = localStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
}

export async function mockGetDocuments() {
  initMockData();
  const docs = read(DOCS_KEY, []);
  const userRaw = localStorage.getItem("user");
  const user = userRaw ? JSON.parse(userRaw) : null;

  if (user?.role === "admin") {
    return docs.sort((a, b) => new Date(b.uploadedAt) - new Date(a.uploadedAt));
  }

  return docs
    .filter((d) => d.uploadedByEmail === user?.email)
    .sort((a, b) => new Date(b.uploadedAt) - new Date(a.uploadedAt));
}

export async function mockUploadDocument(file) {
  initMockData();
  const docs = read(DOCS_KEY, []);
  const userRaw = localStorage.getItem("user");
  const user = userRaw ? JSON.parse(userRaw) : null;
  const text = await file.text().catch(() => "Nội dung file nhị phân mock");

  docs.unshift({
    id: docs.length ? Math.max(...docs.map((d) => d.id)) + 1 : 1,
    fileName: file.name,
    fileType: file.type || "application/octet-stream",
    fileSize: file.size,
    status: "pending",
    uploadedBy: user?.fullName || "Công dân",
    uploadedByEmail: user?.email || "citizen@demo.vn",
    uploadedAt: now(),
    signedAt: null,
    qrCodeData: null,
    fileContent: text.slice(0, 5000),
  });

  write(DOCS_KEY, docs);
  return { success: true, message: "Tải tài liệu thành công" };
}

export async function mockSignDocument(id, payload) {
  initMockData();
  const docs = read(DOCS_KEY, []);
  const index = docs.findIndex((d) => d.id === id);
  if (index === -1) {
    return { success: false, message: "Không tìm thấy tài liệu" };
  }

  docs[index] = {
    ...docs[index],
    status: "signed",
    signedAt: now(),
    qrCodeData: payload?.qrCodeData || JSON.stringify({ id, status: "signed" }),
  };

  write(DOCS_KEY, docs);
  return { success: true, message: "Ký tài liệu thành công" };
}

export function mockGetDownloadUrl(id) {
  initMockData();
  const docs = read(DOCS_KEY, []);
  const doc = docs.find((d) => d.id === id);
  const blob = new Blob([
    doc?.fileContent || `Mock file for document #${id}`,
  ], { type: doc?.fileType || "text/plain;charset=utf-8" });
  return URL.createObjectURL(blob);
}
