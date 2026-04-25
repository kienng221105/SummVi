"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useCallback } from "react";
import { Mail, Lock, CheckCircle2, ShieldCheck, ArrowLeft, Loader2 } from "lucide-react";

import { getCurrentUser, loginUser, loginWithGoogle, registerUser } from "../lib/api";
import { useSessionGuard } from "../lib/session-guard";
import { createSession, mergeSessionWithUser, saveSession } from "../lib/session";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "1044526588457-hg06sug0eg9ocit1djhmgh2c7be06ijn.apps.googleusercontent.com";

/**
 * AuthPage Component - Optimized Version V3
 * Features:
 * - Optimized Google GIS integration with proper script cleanup/check.
 * - Centralized session management and error handling.
 * - Enhanced UI components with Tailwind CSS for modern look & feel.
 */
export default function AuthPage({ mode = "login", title = "Tối ưu hóa hiệu suất", subtitle = "Khám phá sức mạnh của AI trong việc tóm tắt tài liệu." }) {
  const router = useRouter();
  const { booting } = useSessionGuard({ mode: "public" });
  const isLogin = mode === "login";
  
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    acceptedTerms: false,
  });
  
  const [status, setStatus] = useState({
    loading: false,
    error: "",
  });
  
  const googleBtnRef = useRef(null);

  const handleInputChange = (e) => {
    const { id, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [id]: type === "checkbox" ? checked : value
    }));
  };

  const handleSessionAndRedirect = useCallback(async (token, email = "") => {
    const baseSession = createSession(token, email);
    const currentUser = await getCurrentUser(baseSession.token);
    const refreshedSession = mergeSessionWithUser(baseSession, currentUser);
    saveSession(refreshedSession);
    router.replace(refreshedSession.role === "admin" ? "/admin" : "/");
    router.refresh();
  }, [router]);

  const handleGoogleCallback = useCallback(async (response) => {
    setStatus({ loading: true, error: "" });
    try {
      const data = await loginWithGoogle(response.credential);
      await handleSessionAndRedirect(data.access_token);
    } catch (err) {
      setStatus({ loading: false, error: err.message || "Đăng nhập Google thất bại." });
    }
  }, [handleSessionAndRedirect]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    window.__handleGoogleCallback = handleGoogleCallback;

    const initGoogleBtn = () => {
      if (window.google?.accounts?.id && googleBtnRef.current) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleGoogleCallback,
        });
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: isLogin ? "signin_with" : "signup_with",
          shape: "rectangular",
          width: "100%",
        });
      }
    };

    const scriptId = "google-gsi-client";
    let script = document.getElementById(scriptId);

    if (!script) {
      script = document.createElement("script");
      script.id = scriptId;
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = initGoogleBtn;
      document.head.appendChild(script);
    } else {
      initGoogleBtn();
    }
  }, [isLogin, handleGoogleCallback]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus({ loading: true, error: "" });

    try {
      if (!isLogin) {
        if (!formData.acceptedTerms) throw new Error("Cần đồng ý với điều khoản dịch vụ.");
        if (formData.password !== formData.confirmPassword) throw new Error("Mật khẩu xác nhận không khớp.");
        
        await registerUser({ email: formData.email, password: formData.password });
      }

      const data = await loginUser({ email: formData.email, password: formData.password });
      await handleSessionAndRedirect(data.access_token, formData.email);
    } catch (err) {
      setStatus({ loading: false, error: err.message || "Không thể thực hiện yêu cầu." });
    }
  };

  if (booting) {
    return <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
    </div>;
  }

  return (
    <main className="min-h-screen flex bg-white font-sans selection:bg-indigo-100">
      {/* Banner Section */}
      <section className="hidden lg:flex w-1/2 bg-[#121926] relative overflow-hidden items-center justify-center p-16">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-600/20 to-transparent z-0" />
        
        {/* Animated Background Orbs */}
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl animate-pulse delay-700" />

        <div className="relative z-10 max-w-lg text-white">
          <div className="flex items-center gap-3 mb-12">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center font-bold text-xl shadow-lg shadow-indigo-600/30">SV</div>
            <span className="text-2xl font-bold tracking-tight">SummVi</span>
          </div>

          <h1 className="text-5xl font-extrabold tracking-tight mb-6 leading-tight">
            {title}
          </h1>
          <p className="text-lg text-slate-400 mb-12 leading-relaxed">
            {subtitle}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {[
              { label: "Nhanh hơn", value: "10x", icon: Loader2 },
              { label: "Độ chính xác", value: "98%", icon: CheckCircle2 },
              { label: "Tài liệu", value: "+50k", icon: ShieldCheck }
            ].map((stat) => (
              <div key={stat.label} className="bg-white/5 backdrop-blur-md border border-white/10 p-6 rounded-2xl">
                <div className="text-3xl font-bold text-white mb-1">{stat.value}</div>
                <div className="text-sm text-slate-400 font-medium">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Form Section */}
      <section className="w-full lg:w-1/2 flex flex-col justify-center px-8 sm:px-16 lg:px-24 py-12">
        <div className="max-w-md w-full mx-auto">
          {!isLogin && (
            <Link href="/login" className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-indigo-600 transition-colors mb-8">
              <ArrowLeft size={16} /> Quay lại đăng nhập
            </Link>
          )}

          <div className="mb-10">
            <h2 className="text-3xl font-bold text-slate-900 mb-2">
              {isLogin ? "Chào mừng trở lại" : "Tạo tài khoản mới"}
            </h2>
            <p className="text-slate-500">
              {isLogin ? "Đăng nhập để tiếp tục công việc của bạn." : "Trải nghiệm dịch vụ tóm tắt thông minh ngay hôm nay."}
            </p>
          </div>

          {/* Social Auth */}
          <div className="mb-8">
            <div ref={googleBtnRef} className="w-full" />
          </div>

          <div className="relative mb-8">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200"></div></div>
            <div className="relative flex justify-center text-xs uppercase"><span className="bg-white px-4 text-slate-400 font-medium">Hoặc với email</span></div>
          </div>

          {/* Main Auth Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-700 ml-1">Email</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                  id="email"
                  type="email"
                  required
                  className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all text-slate-900 placeholder:text-slate-400"
                  placeholder="name@example.com"
                  value={formData.email}
                  onChange={handleInputChange}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center ml-1">
                <label className="text-sm font-semibold text-slate-700">Mật khẩu</label>
                {isLogin && <span className="text-xs font-medium text-indigo-600 hover:underline cursor-pointer">Quên mật khẩu?</span>}
              </div>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                  id="password"
                  type="password"
                  required
                  minLength={8}
                  className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all text-slate-900 placeholder:text-slate-400"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={handleInputChange}
                />
              </div>
            </div>

            {!isLogin && (
              <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-700 ml-1">Xác nhận mật khẩu</label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    id="confirmPassword"
                    type="password"
                    required
                    className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all text-slate-900 placeholder:text-slate-400"
                    placeholder="••••••••"
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                  />
                </div>
              </div>
            )}

            <div className="flex items-center gap-3 py-2">
              <input
                id={isLogin ? "remember" : "acceptedTerms"}
                type="checkbox"
                className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                checked={isLogin ? true : formData.acceptedTerms}
                onChange={handleInputChange}
              />
              <label htmlFor={isLogin ? "remember" : "acceptedTerms"} className="text-sm text-slate-600 leading-tight">
                {isLogin ? "Ghi nhớ phiên đăng nhập của tôi" : "Tôi đồng ý với Điều khoản dịch vụ và Chính sách bảo mật."}
              </label>
            </div>

            {status.error && (
              <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-red-600 text-sm font-medium flex items-center gap-3">
                <div className="w-1.5 h-1.5 bg-red-600 rounded-full" />
                {status.error}
              </div>
            )}

            <button
              type="submit"
              disabled={status.loading}
              className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-bold rounded-xl shadow-lg shadow-indigo-600/20 transition-all flex items-center justify-center gap-3"
            >
              {status.loading && <Loader2 className="w-5 h-5 animate-spin" />}
              {isLogin ? "Đăng nhập ngay" : "Tạo tài khoản"}
            </button>
          </form>

          <p className="mt-10 text-center text-slate-600">
            {isLogin ? "Chưa có tài khoản?" : "Đã có tài khoản?"}{" "}
            <Link href={isLogin ? "/register" : "/login"} className="text-indigo-600 font-bold hover:underline">
              {isLogin ? "Đăng ký miễn phí" : "Đăng nhập tại đây"}
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}
