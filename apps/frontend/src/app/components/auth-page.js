"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { getCurrentUser, loginUser, registerUser } from "../lib/api";
import { useSessionGuard } from "../lib/session-guard";
import { createSession, mergeSessionWithUser, saveSession } from "../lib/session";

export default function AuthPage({ mode, title, subtitle }) {
  const router = useRouter();
  const { booting } = useSessionGuard({ mode: "public" });
  const isLogin = mode === "login";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fullName = useMemo(
    () => `${firstName.trim()} ${lastName.trim()}`.trim(),
    [firstName, lastName],
  );

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      if (!isLogin && !acceptedTerms) {
        throw new Error("Cần đồng ý với điều khoản trước khi tạo tài khoản.");
      }

      if (isLogin) {
        const token = await loginUser({ email, password });
        const baseSession = createSession(token.access_token, email);
        const currentUser = await getCurrentUser(baseSession.token);
        const refreshedSession = mergeSessionWithUser(baseSession, currentUser);
        saveSession(refreshedSession);
        router.replace(refreshedSession.role === "admin" ? "/admin" : "/");
        router.refresh();
        return;
      }

      await registerUser({ email, password });
      const token = await loginUser({ email, password });
      const baseSession = createSession(token.access_token, email || fullName);
      const currentUser = await getCurrentUser(baseSession.token);
      const refreshedSession = mergeSessionWithUser(baseSession, currentUser);
      saveSession(refreshedSession);
      router.replace(refreshedSession.role === "admin" ? "/admin" : "/");
      router.refresh();
    } catch (requestError) {
      setError(requestError.message || "Không thể thực hiện yêu cầu.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-container">
      {booting ? <div className="app-loading" aria-hidden="true" /> : null}
      <section className={`auth-banner ${isLogin ? "login-banner" : "register-banner"}`}>
        <div className="banner-content">
          <div className="logo">
            <div className="logo-icon">SV</div>
            <h2>SummVi</h2>
          </div>

          <h1>{title}</h1>
          <p>{subtitle}</p>

          {isLogin ? (
            <div className="stats-cards">
              <div className="stat-card">
                <h3>10x</h3>
                <p>Nhanh hơn</p>
              </div>
              <div className="stat-card">
                <h3>98%</h3>
                <p>Độ chính xác</p>
              </div>
              <div className="stat-card">
                <h3>+50k</h3>
                <p>Tài liệu</p>
              </div>
            </div>
          ) : null}
        </div>
        <div className="circle-decoration circle-1" />
        <div className="circle-decoration circle-2" />
      </section>

      <section className="auth-form-wrapper">
        <div className="form-container">
          {!isLogin ? (
            <Link className="back-btn" href="/login">
              Quay lại
            </Link>
          ) : null}

          <div className="form-header">
            <h2>{isLogin ? "Chào mừng trở lại" : "Tạo tài khoản mới"}</h2>
            <p>
              {isLogin
                ? "Đăng nhập để tiếp tục công việc tóm tắt."
                : "Đăng ký để trải nghiệm dịch vụ tóm tắt thông minh."}
            </p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            {!isLogin ? (
              <div className="input-row">
                <div className="input-group">
                  <label htmlFor="first-name">Họ</label>
                  <input
                    id="first-name"
                    onChange={(event) => setFirstName(event.target.value)}
                    placeholder="Nguyễn"
                    type="text"
                    value={firstName}
                  />
                </div>
                <div className="input-group">
                  <label htmlFor="last-name">Tên</label>
                  <input
                    id="last-name"
                    onChange={(event) => setLastName(event.target.value)}
                    placeholder="Kiên"
                    type="text"
                    value={lastName}
                  />
                </div>
              </div>
            ) : null}

            <div className="input-group">
              <label htmlFor="email">Email</label>
              <div className="input-wrapper">
                <span className="input-prefix">@</span>
                <input
                  id="email"
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="kien.nguyen@example.com"
                  required
                  type="email"
                  value={email}
                />
              </div>
            </div>

            <div className="input-group">
              <label htmlFor="password">Mật khẩu</label>
              <div className="input-wrapper">
                <span className="input-prefix">*</span>
                <input
                  id="password"
                  minLength={8}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={isLogin ? "Nhập mật khẩu" : "Tạo mật khẩu mạnh"}
                  required
                  type="password"
                  value={password}
                />
              </div>
            </div>

            {isLogin ? (
              <div className="form-options">
                <label className="remember-me">
                  <input type="checkbox" />
                  <span>Ghi nhớ tôi</span>
                </label>
                <span className="forgot-pw">Bảo mật hệ thống</span>
              </div>
            ) : (
              <div className="form-options">
                <label className="remember-me wide">
                  <input
                    checked={acceptedTerms}
                    onChange={(event) => setAcceptedTerms(event.target.checked)}
                    type="checkbox"
                  />
                  <span>Tôi đồng ý với điều khoản dịch vụ và chính sách bảo mật.</span>
                </label>
              </div>
            )}

            {error ? <p className="inline-error">{error}</p> : null}

            <button className="auth-btn" disabled={submitting} type="submit">
              {submitting ? "Đang xử lý..." : isLogin ? "Đăng nhập ngay" : "Đăng ký tài khoản"}
            </button>
          </form>

          <p className="auth-footer">
            {isLogin ? "Chưa có tài khoản?" : "Đã có tài khoản?"}{" "}
            <Link href={isLogin ? "/register" : "/login"}>
              {isLogin ? "Đăng ký ngay" : "Đăng nhập"}
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}
