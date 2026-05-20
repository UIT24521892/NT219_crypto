import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginApi } from "../services/authService";

export default function LoginPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const handleChange = (e) => {
    setForm((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = await loginApi(form);

      if (!data.success) {
        alert(data.message || "Đăng nhập thất bại");
        return;
      }

      localStorage.setItem("accessToken", data.accessToken);
      localStorage.setItem("user", JSON.stringify(data.user));
      navigate(data.user.role === "admin" ? "/admin" : "/citizen");
    } catch (error) {
      alert(error?.response?.data?.message || "Đăng nhập thất bại");
    }
  };

  return (
    <div className="auth-layout shell">
      <div className="auth-hero">
        <span className="hero-badge">Mock mode sẵn sàng để test frontend</span>
        <h1>Cổng thông tin công dân</h1>
        <p>
          Đăng nhập để kiểm tra luồng nộp hồ sơ, danh sách tài liệu, ký số và mã QR
          mà không cần kết nối database thật.
        </p>
        <div className="demo-accounts">
          <div className="demo-card">
            <strong>Admin</strong>
            <span>admin@demo.vn / admin123</span>
          </div>
          <div className="demo-card">
            <strong>Công dân</strong>
            <span>citizen@demo.vn / 123456</span>
          </div>
        </div>
      </div>

      <div className="auth-card">
        <h2>Đăng nhập</h2>
        <p className="muted">Nhập tài khoản để bắt đầu.</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <input name="email" placeholder="Email" value={form.email} onChange={handleChange} />
          <input
            name="password"
            type="password"
            placeholder="Mật khẩu"
            value={form.password}
            onChange={handleChange}
          />
          <button className="btn btn-primary btn-block" type="submit">
            Đăng nhập
          </button>
        </form>

        <p className="switch-text">
          Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
        </p>
      </div>
    </div>
  );
}
