"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { getCurrentUser, loginUser, loginWithGoogle, registerUser } from "../lib/api";
import { useSessionGuard } from "../lib/session-guard";
import { createSession, mergeSessionWithUser, saveSession } from "../lib/session";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "1044526588457-hg06sug0eg9ocit1djhmgh2c7be06ijn.apps.googleusercontent.com";

export default function AuthPage({ mode, title, subtitle }) {
  const router = useRouter();
  const { booting } = useSessionGuard({ mode: "public" });
  const isLogin = mode === "login";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const googleBtnRef = useRef(null);

  // Load Google Identity Services script
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleGoogleCallback = async (response) => {
      setSubmitting(true);
      setError("");
      try {
        const token = await loginWithGoogle(response.credential);
        const baseSession = createSession(token.access_token, "");
        const currentUser = await getCurrentUser(baseSession.token);
        const refreshedSession = mergeSessionWithUser(baseSession, currentUser);
        saveSession(refreshedSession);
        router.replace(refreshedSession.role === "admin" ? "/admin" : "/");
        router.refresh();
      } catch (err) {
        setError(err.message || "Đăng nhập Google thất bại.");
      } finally {
        setSubmitting(false);
      }
    };

    // Make callback globally accessible for GIS
    window.__handleGoogleCallback = handleGoogleCallback;

    const existingScript = document.querySelector('script[src*="accounts.google.com/gsi/client"]');
    if (existingScript) {
      // Script already loaded, just initialize
      if (window.google?.accounts?.id) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleGoogleCallback,
        });
        if (googleBtnRef.current) {
          window.google.accounts.id.renderButton(googleBtnRef.current, {
            type: "standard",
            theme: "outline",
            size: "large",
            text: isLogin ? "signin_with" : "signup_with",
            shape: "rectangular",
            width: "100%",
          });
        }
      }
      return;
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleGoogleCallback,
        });
        if (googleBtnRef.current) {
          window.google.accounts.id.renderButton(googleBtnRef.current, {
            type: "standard",
            theme: "outline",
            size: "large",
            text: isLogin ? "signin_with" : "signup_with",
            shape: "rectangular",
            width: "100%",
          });
        }
      }
    };
    document.head.appendChild(script);
  }, [isLogin, router]);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      if (!isLogin && !acceptedTerms) {
        throw new Error("Cần đồng ý với điều khoản trước khi tạo tài khoản.");
      }

      if (!isLogin && password !== confirmPassword) {
        throw new Error("Mật khẩu xác nhận không khớp.");
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
      const baseSession = createSession(token.access_token, email);
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

          {/* Google Sign-In Button */}
          <div className="google-signin-wrapper">
            <div ref={googleBtnRef} className="google-btn-container" />
          </div>

          <div className="auth-divider">
            <span>hoặc</span>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
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

            {!isLogin ? (
              <div className="input-group">
                <label htmlFor="confirm-password">Xác nhận mật khẩu</label>
                <div className="input-wrapper">
                  <span className="input-prefix">*</span>
                  <input
                    id="confirm-password"
                    minLength={8}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Nhập lại mật khẩu"
                    required
                    type="password"
                    value={confirmPassword}
                  />
                </div>
              </div>
            ) : null}

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
