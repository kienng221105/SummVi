"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useCallback } from "react";
import {
  Activity,
  AlertCircle,
  BarChart3,
  CheckCircle,
  Database,
  LayoutDashboard,
  LogOut,
  RefreshCcw,
  Settings,
  ShieldCheck,
  TrendingUp,
  Users,
  X,
} from "lucide-react";

import {
  getAdminAnalytics,
  listLogs,
  listUsers,
  updateUserRole,
} from "../lib/api";
import {
  clearStoredSession,
  isAdminSession,
} from "../lib/session";
import { useSessionGuard } from "../lib/session-guard";

// --- CONSTANTS ---
const NAV_ITEMS = [
  { id: "overview", label: "Tổng quan", icon: LayoutDashboard },
  { id: "users", label: "Quản lý người dùng", icon: Users },
  { id: "logs", label: "Logs và hiệu suất", icon: Activity },
  { id: "model", label: "Giám sát model", icon: BarChart3 },
  { id: "data", label: "Dữ liệu và RAG", icon: Database },
];

const CHART_COLORS = ["#a78bfa", "#60a5fa", "#34d399", "#fb923c", "#f87171", "#94a3b8", "#f472b6", "#c084fc"];

// --- UTILS ---
const formatDate = (value) => {
  if (!value) return "--";
  const normalized = typeof value === "string" && !value.endsWith("Z") && !value.includes("+") ? value + "Z" : value;
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(normalized));
};

const formatMetricValue = (metric) => {
  if (!metric) return "--";
  return `${metric.value}${metric.unit || ""}`;
};

// --- SUB-COMPONENTS (OPTIMIZED) ---

/**
 * Sparkline: Biểu đồ đường mini cho Stat Cards
 */
const Sparkline = ({ points = [], color = "#a78bfa" }) => {
  const memoizedPath = useMemo(() => {
    if (points.length < 2) return null;
    const values = points.map(p => Number(p.value) || 0);
    const min = Math.min(...values);
    const max = Math.max(...values, min + 1);
    const range = max - min;
    const width = 100;
    const height = 30;

    return values.map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  }, [points]);

  if (!memoizedPath) return null;

  return (
    <svg width="100" height="30" viewBox="0 0 100 30" className="opacity-80">
      <path d={memoizedPath} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

/**
 * ChartCard: Container chuẩn cho các loại biểu đồ
 */
const ChartCard = ({ title, subtitle, points = [], type = "area", accent = "#a78bfa", icon: Icon, onClick }) => (
  <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm hover:shadow-md transition-shadow">
    <div className="flex justify-between items-start mb-6">
      <div className="flex gap-3">
        {Icon && <div className="p-2 bg-slate-100 dark:bg-slate-800 rounded-lg text-slate-600 dark:text-slate-400"><Icon size={20} /></div>}
        <div>
          <h3 className="font-semibold text-slate-900 dark:text-white">{title}</h3>
          <p className="text-sm text-slate-500">{subtitle}</p>
        </div>
      </div>
      {onClick && (
        <button onClick={onClick} className="text-xs font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400">
          Chi tiết
        </button>
      )}
    </div>
    <div className="h-[200px] flex items-center justify-center">
      {points.length === 0 ? (
        <p className="text-sm text-slate-400 italic">Chưa có dữ liệu</p>
      ) : (
        /* Render Chart Logic Here (SVG based) */
        <div className="w-full text-center text-slate-400 text-xs">[Biểu đồ {type}]</div>
      )}
    </div>
  </div>
);

// --- MAIN COMPONENT ---

export default function AdminConsole() {
  const router = useRouter();
  const { session, setSession, booting } = useSessionGuard({
    mode: "protected",
    requireAdmin: true,
    fallbackPath: "/",
  });

  const [data, setData] = useState({
    users: [],
    logs: [],
    analytics: null,
    loading: true,
    error: ""
  });
  
  const [activeSection, setActiveSection] = useState("overview");
  const [drillDown, setDrillDown] = useState(null);

  const loadAdminData = useCallback(async (token) => {
    setData(prev => ({ ...prev, loading: true, error: "" }));
    try {
      const [userRows, logRows, analyticsPayload] = await Promise.all([
        listUsers(token),
        listLogs(token),
        getAdminAnalytics(token),
      ]);
      setData({
        users: userRows,
        logs: logRows,
        analytics: analyticsPayload,
        loading: false,
        error: ""
      });
    } catch (err) {
      setData(prev => ({ ...prev, loading: false, error: err.message || "Lỗi tải dữ liệu" }));
    }
  }, []);

  useEffect(() => {
    if (!booting && session?.token) {
      loadAdminData(session.token);
    }
  }, [booting, session, loadAdminData]);

  // Derived state
  const metrics = useMemo(() => ({
    overview: data.analytics?.overview || [],
    system: data.analytics?.system_metrics || [],
    charts: data.analytics?.charts || {}
  }), [data.analytics]);

  const handleLogout = () => {
    clearStoredSession();
    setSession(null);
    router.replace("/login");
  };

  if (booting || data.loading && !data.analytics) {
    return <div className="flex h-screen items-center justify-center bg-slate-50 dark:bg-slate-950 text-slate-500 italic">Đang tải dữ liệu...</div>;
  }

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950 font-sans text-slate-900 dark:text-slate-100">
      {/* Sidebar */}
      <aside className="w-72 bg-[#121926] text-slate-300 flex flex-col fixed h-full z-50">
        <div className="p-8 flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-bold text-xl">SV</div>
          <span className="text-xl font-bold text-white tracking-tight">SummVi <span className="text-xs bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded ml-1">ADMIN</span></span>
        </div>

        <nav className="flex-1 px-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                  isActive 
                    ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20" 
                    : "hover:bg-slate-800/50 hover:text-white"
                }`}
              >
                <Icon size={20} />
                <span className="font-medium">{item.label}</span>
              </button>
            );
          })}
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
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white capitalize">
              {NAV_ITEMS.find(n => n.id === activeSection)?.label}
            </h1>
            <p className="text-slate-500 mt-1">Chào mừng trở lại, hệ thống đang vận hành ổn định.</p>
          </div>

          <div className="flex items-center gap-4">
            <button 
              onClick={() => loadAdminData(session.token)}
              className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition-all"
            >
              <RefreshCcw size={16} /> Làm mới
            </button>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-full text-xs font-semibold">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              Đã đồng bộ
            </div>
          </div>
        </header>

        {/* Content Stack */}
        <div className="space-y-8">
          {activeSection === "overview" && (
            <>
              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {metrics.overview.map((metric, idx) => (
                  <div key={metric.label} className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
                    <div className="flex justify-between items-start mb-4">
                      <div className={`p-2 rounded-lg ${idx === 3 ? "bg-red-100 text-red-600" : "bg-indigo-100 text-indigo-600"}`}>
                        <Activity size={20} />
                      </div>
                      <Sparkline points={idx === 0 ? metrics.charts.request_volume : []} color={idx === 3 ? "#f87171" : "#a78bfa"} />
                    </div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white">{formatMetricValue(metric)}</div>
                    <div className="text-sm font-medium text-slate-500 mt-1">{metric.label}</div>
                    <div className="text-[11px] text-slate-400 mt-2 uppercase tracking-wider">{metric.detail}</div>
                  </div>
                ))}
              </div>

              {/* Charts Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <ChartCard 
                  title="Lưu lượng Request" 
                  subtitle="7 ngày gần nhất" 
                  points={metrics.charts.request_volume} 
                  icon={TrendingUp}
                  onClick={() => setDrillDown({ title: "Lưu lượng Request", data: metrics.charts.request_volume })}
                />
                <ChartCard 
                  title="Tỷ lệ Lỗi" 
                  subtitle="Theo dõi HTTP 5xx/4xx" 
                  points={metrics.charts.error_volume} 
                  accent="#f87171"
                  icon={AlertCircle}
                />
              </div>
            </>
          )}

          {/* Other sections would follow similar optimized patterns */}
          {activeSection !== "overview" && (
            <div className="p-20 text-center border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-2xl text-slate-400">
              Chế độ xem {activeSection} đang được tối ưu hóa...
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
