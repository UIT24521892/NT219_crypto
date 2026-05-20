import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerApi } from "../services/authService";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
    citizenId: "",
    phoneNumber: "",
  });

  const handleChange = (e) => {
    setForm((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (form.password !== form.confirmPassword) {
      alert("Mật khẩu xác nhận không khớp");
      return;
    }

    try {
      const data = await registerApi(form);
      if (!data.success) {
        alert(data.message || "Đăng ký thất bại");
        return;
      }

      alert(data.message || "Đăng ký thành công");
      navigate("/login");
    } catch (error) {
      alert(error?.response?.data?.message || "Đăng ký thất bại");
    }
  };

  return (
    <div className="auth-layout shell auth-layout-single">
      <div className="auth-card auth-card-wide">
        <h2>Tạo tài khoản công dân</h2>
        <p className="muted">Điền thông tin để tạo tài khoản test giao diện.</p>

        <form onSubmit={handleSubmit} className="auth-form grid-form">
          <input name="fullName" placeholder="Họ và tên" value={form.fullName} onChange={handleChange} />
          <input name="email" placeholder="Email" value={form.email} onChange={handleChange} />
          <input name="citizenId" placeholder="Số CCCD" value={form.citizenId} onChange={handleChange} />
          <input name="phoneNumber" placeholder="Số điện thoại" value={form.phoneNumber} onChange={handleChange} />
          <input name="password" type="password" placeholder="Mật khẩu" value={form.password} onChange={handleChange} />
          <input
            name="confirmPassword"
            type="password"
            placeholder="Xác nhận mật khẩu"
            value={form.confirmPassword}
            onChange={handleChange}
          />
          <button className="btn btn-primary btn-block grid-full" type="submit">
            Đăng ký
          </button>
        </form>

        <p className="switch-text">
          Đã có tài khoản? <Link to="/login">Quay lại đăng nhập</Link>
        </p>
      </div>
    </div>
  );
}
