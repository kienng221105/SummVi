"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { User, Shield, Mail, Activity, LogOut, LayoutDashboard, ChevronRight, Settings as SettingsIcon, Bell, HelpCircle } from "lucide-react";

import { clearStoredSession, isAdminSession } from "../lib/session";
import { useSessionGuard } from "../lib/session-guard";

/**
 * SettingsConsole Component - Optimized Version V3
 * Part of the Lumina Admin Design System for SummVi.
 */
export default function SettingsConsole() {
  const router = useRouter();
  const { session, setSession, booting } = useSessionGuard({ mode: "protected" });

  const handleLogout = () => {
    clearStoredSession();
    setSession(null);
    router.replace("/login");
    router.refresh();
  };

  const getInitials = (email) => {
    if (!email) return "SV";
    return email.split("@")[0].slice(0, 2).toUpperCase();
  };

  const adminSession = isAdminSession(session);

  if (booting) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Activity className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex font-sans">
      {/* Sidebar */}
      <aside className="w-72 bg-[#121926] text-slate-300 flex flex-col fixed h-full z-50">
        <div className="p-8 flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-bold text-xl">SV</div>
          <span className="text-xl font-bold text-white tracking-tight">SummVi</span>
        </div>

        <nav className="flex-1 px-4 space-y-2">
          <Link href="/" className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-colors">
            <LayoutDashboard size={20} />
            <span className="font-medium">Về Workspace</span>
          </Link>
          
          <div className="pt-4 pb-2 px-4 uppercase text-[10px] font-bold tracking-wider text-slate-500">Tài khoản</div>
          
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-indigo-600 text-white shadow-lg shadow-indigo-600/20">
            <User size={20} />
            <span className="font-medium">Hồ sơ cá nhân</span>
          </button>

          {adminSession && (
            <Link href="/admin" className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-slate-800 transition-colors">
              <Shield size={20} />
              <span className="font-medium">Quản trị hệ thống</span>
            </Link>
          )}
        </nav>

        <div className="p-6 border-t border-slate-800">
          <button onClick={handleLogout} className="flex items-center gap-3 text-slate-400 hover:text-red-400 transition-colors w-full px-4">
            <LogOut size={20} />
            <span className="font-medium">Đăng xuất</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-72 p-10">
        <header className="flex justify-between items-center mb-10">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <span>Hệ thống</span>
            <ChevronRight size={14} />
            <span className="text-indigo-600 font-medium">Hồ sơ cá nhân</span>
          </div>

          <div className="flex items-center gap-4">
            <button className="p-2 text-slate-400 hover:text-slate-600 transition-colors"><Bell size={20} /></button>
            <button className="p-2 text-slate-400 hover:text-slate-600 transition-colors"><HelpCircle size={20} /></button>
            <button className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold shadow-md shadow-indigo-600/20">Nâng cấp Gói</button>
          </div>
        </header>

        <div className="max-w-4xl">
          {/* Profile Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-8">
            <div className="h-32 bg-gradient-to-r from-indigo-500 to-violet-500" />
            <div className="px-8 pb-8">
              <div className="relative -mt-12 mb-6 flex items-end justify-between">
                <div className="p-1 bg-white rounded-2xl">
                  <div className="w-24 h-24 bg-slate-100 rounded-xl flex items-center justify-center text-indigo-600 font-bold text-3xl border-4 border-white shadow-sm relative">
                    {getInitials(session?.email)}
                    <span className="absolute bottom-1 right-1 w-4 h-4 bg-emerald-500 border-2 border-white rounded-full" />
                  </div>
                </div>
                <button className="px-6 py-2 bg-indigo-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-indigo-600/20 hover:bg-indigo-700 transition-all">
                  Chỉnh sửa hồ sơ
                </button>
              </div>

              <div className="mb-8">
                <h2 className="text-2xl font-bold text-slate-900">{session?.email?.split('@')[0]}</h2>
                <p className="text-slate-500 font-medium">Thành viên cao cấp @ SummVi Intelligence</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-6">
                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Địa chỉ Email</label>
                    <div className="flex items-center gap-3 p-4 bg-slate-50 border border-slate-100 rounded-xl">
                      <Mail size={18} className="text-slate-400" />
                      <span className="font-semibold text-slate-700">{session?.email || "Chưa cập nhật"}</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Mã người dùng (User ID)</label>
                    <div className="flex items-center gap-3 p-4 bg-slate-50 border border-slate-100 rounded-xl">
                      <Activity size={18} className="text-slate-400" />
                      <span className="font-mono text-sm text-slate-700">{session?.userId || "USR-UNKNOWN"}</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-6">
                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Vai trò (Role)</label>
                    <div className="flex items-center gap-3 p-4 bg-slate-50 border border-slate-100 rounded-xl">
                      <Shield size={18} className="text-slate-400" />
                      <span className="font-semibold text-slate-700 capitalize">{session?.role || "User"}</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Trạng thái tài khoản</label>
                    <div className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-100 rounded-xl">
                      <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                      <span className="font-bold text-emerald-700">Đang hoạt động</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Stats or Activity */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
             <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <div className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Gói tài khoản</div>
                <div className="text-2xl font-black text-indigo-600 mb-1">Business Pro</div>
                <div className="text-sm text-slate-500">Hết hạn vào 24/12/2024</div>
             </div>
             <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm md:col-span-2">
                <div className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Hoạt động gần đây</div>
                <div className="space-y-4">
                  {[
                    { act: "Đăng nhập thành công", time: "2 giờ trước" },
                    { act: "Cập nhật ảnh đại diện", time: "1 ngày trước" }
                  ].map((item, i) => (
                    <div key={i} className="flex justify-between items-center text-sm">
                      <span className="text-slate-700 font-medium">{item.act}</span>
                      <span className="text-slate-400">{item.time}</span>
                    </div>
                  ))}
                </div>
             </div>
          </div>
        </div>
      </main>
    </div>
  );
}
