"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
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

const NAV_ITEMS = [
  { id: "overview", label: "Tổng quan", icon: LayoutDashboard },
  { id: "users", label: "Quản lý người dùng", icon: Users },
  { id: "logs", label: "Logs và hiệu suất", icon: Activity },
  { id: "model", label: "Giám sát model", icon: BarChart3 },
  { id: "data", label: "Dữ liệu và RAG", icon: Database },
];

function formatDate(value) {
  if (!value) {
    return "--";
  }
  // Ensure the timestamp is treated as UTC if no timezone info is present
  const normalized = typeof value === "string" && !value.endsWith("Z") && !value.includes("+") ? value + "Z" : value;
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(normalized));
}

function formatMetricValue(metric) {
  if (!metric) {
    return "--";
  }
  return `${metric.value}${metric.unit || ""}`;
}

// --- NEW ANALYTICS COMPONENTS ---

function Sparkline({ points = [], color = "#8884d8" }) {
  if (points.length < 2) return null;
  const values = points.map(p => Number(p.value) || 0);
  const min = Math.min(...values);
  const max = Math.max(...values, min + 1);
  const range = max - min;

  const width = 100;
  const height = 30;

  const d = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="sparkline">
      <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function AreaChart({ points = [], color = "#a78bfa" }) {
  if (points.length < 2) return <p className="empty-state">Chưa đủ dữ liệu.</p>;
  const values = points.map(p => Number(p.value) || 0);
  const maxValue = Math.max(...values, 10);
  const width = 100;
  const height = 40;

  const areaD = [
    `M 0 ${height}`,
    ...values.map((v, i) => `L ${(i / (values.length - 1)) * width} ${height - (v / maxValue) * height}`),
    `L ${width} ${height}`,
    'Z'
  ].join(' ');

  const lineD = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - (v / maxValue) * height;
    return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
  }).join(' ');

  return (
    <div className="svg-chart-container">
      <svg width="100%" height="120px" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.4" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaD} fill={`url(#grad-${color})`} />
        <path d={lineD} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
      <div className="chart-x-axis">
        {points.map((p, i) => (i % 2 === 0 ? <span key={p.label}>{p.label}</span> : null))}
      </div>
    </div>
  );
}

function DonutChart({ points = [] }) {
  if (points.length === 0) return null;
  const colors = ["#a78bfa", "#60a5fa", "#34d399", "#fb923c", "#f87171", "#94a3b8"];
  const total = points.reduce((acc, p) => acc + (Number(p.value) || 0), 0);
  const displayTotal = Number.isInteger(total) ? total : total.toFixed(3);
  let currentAngle = 0;

  return (
    <div className="donut-container">
      <svg width="140" height="140" viewBox="0 0 42 42" className="donut">
        <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--bg-panel)" strokeWidth="5" />
        {points.map((p, i) => {
          const val = (Number(p.value) || 0);
          const percent = total > 0 ? (val / total) * 100 : 0;
          const offset = 100 - currentAngle + 25;
          currentAngle += percent;
          return (
            <circle
              key={p.label}
              cx="21" cy="21" r="15.915"
              fill="transparent"
              stroke={colors[i % colors.length]}
              strokeWidth="5"
              strokeDasharray={`${percent} ${100 - percent}`}
              strokeDashoffset={offset}
            />
          );
        })}
        <g className="donut-text">
          <text x="21" y="21" dy="-1" className="donut-number">{displayTotal}</text>
          <text x="21" y="21" dy="4" className="donut-label">Total</text>
        </g>
      </svg>
      <div className="donut-legend">
        {points.map((p, i) => (
          <div key={p.label} className="legend-item">
            <span className="dot" style={{ backgroundColor: colors[i % colors.length] }} />
            <span className="label text-truncate">{p.label}</span>
            <span className="value">{p.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DetailedDonutChart({ points = [] }) {
  if (points.length === 0) return null;
  const colors = ["#a78bfa", "#60a5fa", "#34d399", "#fb923c", "#f87171", "#94a3b8", "#f472b6", "#c084fc"];
  const total = points.reduce((acc, p) => acc + (Number(p.value) || 0), 0);
  const displayTotal = Number.isInteger(total) ? total : total.toFixed(2);
  let currentAngle = 0;

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "60px", padding: "20px 0" }}>
      <svg width="240" height="240" viewBox="0 0 42 42" style={{ transform: "rotate(-90deg)", filter: "drop-shadow(0 4px 6px rgba(0,0,0,0.1))" }}>
        <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="#f1f5f9" strokeWidth="6" />
        {points.map((p, i) => {
          const val = (Number(p.value) || 0);
          const percent = total > 0 ? (val / total) * 100 : 0;
          const offset = 100 - currentAngle + 25;
          currentAngle += percent;
          return (
            <circle
              key={p.label}
              cx="21" cy="21" r="15.915"
              fill="transparent"
              stroke={colors[i % colors.length]}
              strokeWidth="6"
              strokeDasharray={`${percent} ${100 - percent}`}
              strokeDashoffset={offset}
              style={{ cursor: "pointer", transition: "stroke-width 0.2s" }}
            >
              <title>{`${p.label}: ${val}`}</title>
            </circle>
          );
        })}
        <g style={{ transform: "rotate(90deg)", transformOrigin: "center" }}>
          <text x="21" y="21" dy="0" fill="#1f2937" fontSize="0.4rem" fontWeight="bold" textAnchor="middle">{displayTotal.toLocaleString("vi-VN")}</text>
          <text x="21" y="21" dy="5" fill="#6b7280" fontSize="0.25rem" textAnchor="middle">Tổng</text>
        </g>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: "14px", maxHeight: "240px", overflowY: "auto", paddingRight: "10px" }}>
        {points.map((p, i) => (
          <div key={p.label} style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "15px" }}>
            <span style={{ width: "12px", height: "12px", borderRadius: "50%", backgroundColor: colors[i % colors.length] }} />
            <span style={{ color: "#4b5563", flex: 1, minWidth: "120px" }}>{p.label}</span>
            <strong style={{ color: "#111827" }}>{p.value}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function BarChart({ points = [], color = "#3b82f6" }) {
  if (points.length === 0) return <p className="empty-state">Chưa đủ dữ liệu.</p>;
  const values = points.map(p => Number(p.value) || 0);
  const maxValue = Math.max(...values, 10);
  const width = 100;
  const height = 40;
  const barWidth = width / values.length - 2;

  return (
    <div className="svg-chart-container">
      <svg width="100%" height="120px" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        {values.map((v, i) => {
          const x = i * (width / values.length) + 1;
          const h = (v / maxValue) * height;
          const y = height - h;
          return (
            <rect key={i} x={x} y={y} width={barWidth > 0 ? barWidth : 1} height={h} fill={color} opacity="0.8" rx="0.5" />
          );
        })}
      </svg>
      <div className="chart-x-axis">
        {points.map((p, i) => (<span key={p.label}>{p.label}</span>))}
      </div>
    </div>
  );
}

function DetailedComboChart({ points = [], color = "#3b82f6" }) {
  if (points.length === 0) return null;
  const values = points.map((p) => Number(p.value) || 0);
  const maxVal = Math.max(...values, 10);
  const width = 800;
  const height = 300;
  const paddingX = 60;
  const paddingY = 40;
  const graphWidth = width - paddingX * 2;
  const graphHeight = height - paddingY * 2;
  const barWidth = graphWidth / values.length - 10;

  // Generate line points
  const getPoint = (i, v) => {
    const x = paddingX + i * (graphWidth / values.length) + 5 + (barWidth > 0 ? barWidth : 10) / 2;
    const y = paddingY + graphHeight - (v / maxVal) * graphHeight;
    return { x, y };
  };

  const polyPoints = points.map((p, i) => {
    const pt = getPoint(i, Number(p.value) || 0);
    return `${pt.x},${pt.y}`;
  }).join(" ");

  return (
    <div style={{ width: "100%", overflowX: "auto" }}>
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} style={{ minWidth: "600px" }}>
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
          const y = paddingY + graphHeight - graphHeight * ratio;
          return (
            <g key={i}>
              <line x1={paddingX} y1={y} x2={width - paddingX} y2={y} stroke="var(--border)" strokeDasharray="4 4" opacity="0.6" />
              <text x={paddingX - 10} y={y + 5} textAnchor="end" fill="var(--text-secondary)" fontSize="12">
                {Math.round(maxVal * ratio).toLocaleString()}
              </text>
            </g>
          );
        })}

        {/* Bars (Background layer) */}
        {points.map((p, i) => {
          const v = Number(p.value) || 0;
          const h = (v / maxVal) * graphHeight;
          const x = paddingX + i * (graphWidth / values.length) + 5;
          const y = paddingY + graphHeight - h;
          return (
            <rect key={`bar-${i}`} x={x} y={y} width={barWidth > 0 ? barWidth : 10} height={h} fill={color} opacity="0.3" rx="2">
              <title>{`${p.label}: ${v}`}</title>
            </rect>
          );
        })}

        {/* Line (Foreground layer) */}
        <polyline points={polyPoints} fill="none" stroke={color} strokeWidth="3" />

        {/* Dots & Labels */}
        {points.map((p, i) => {
          const v = Number(p.value) || 0;
          const { x, y } = getPoint(i, v);
          const barX = paddingX + i * (graphWidth / values.length) + 5;
          return (
            <g key={`dot-${i}`} className="detailed-point group">
              <circle cx={x} cy={y} r="5" fill={color} stroke="var(--bg-panel)" strokeWidth="2" style={{ cursor: "pointer" }}>
                <title>{`${p.label}: ${v}`}</title>
              </circle>
              {/* Tooltip value on hover - handled purely by CSS using .group:hover .chart-tooltip-text if we wanted, but static is fine for colab feel */}
              {values.length < 15 && (
                <text x={x} y={y - 12} textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="bold" opacity="0.8">
                  {v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v}
                </text>
              )}
              {/* X Axis labels */}
              <text x={x} y={paddingY + graphHeight + 20} textAnchor="middle" fill="var(--text-secondary)" fontSize="11" transform={`rotate(-25 ${x} ${paddingY + graphHeight + 20})`}>
                {p.label.length > 12 ? p.label.substring(0, 12) + "..." : p.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function DrillDownModal({ title, data, type, accent, onClose }) {
  const [isClosing, setIsClosing] = useState(false);

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      onClose();
    }, 200);
  };

  const validValues = (data || []).map(row => Number(row.value)).filter(v => !isNaN(v));
  const total = validValues.reduce((sum, v) => sum + v, 0);
  const avg = validValues.length ? Math.round(total / validValues.length) : 0;
  const max = validValues.length ? Math.max(...validValues) : 0;

  return (
    <>
      <div className={`modal-overlay-bg ${isClosing ? "closing" : ""}`} onClick={handleClose} />

      <div className="modal-container-wrapper">
        <div className={`modal-content ${isClosing ? "closing" : ""}`}>
          <div className="modal-header">
            <h3 style={{ fontSize: "18px", fontWeight: "600", color: "#111827", margin: 0 }}>Chi tiết biểu đồ: {title}</h3>
            <button onClick={handleClose} className="btn-icon"><X size={20} /></button>
          </div>
          <div className="modal-body" style={{ padding: "0 24px", overflowY: "auto" }}>
            {type && (
              <div style={{ marginBottom: "1rem", overflow: "visible" }}>
                {type === "donut" ? (
                  <DetailedDonutChart points={data} />
                ) : (
                  <DetailedComboChart points={data} color={accent} />
                )}
              </div>
            )}

            <div style={{
              display: "grid", gridTemplateColumns: "1fr 1px 1fr", gap: "24px",
              borderTop: "1px solid var(--border)", paddingTop: "20px", marginBottom: "20px", alignItems: "center"
            }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "14px", color: "var(--text-secondary)" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Tổng Ghi Nhận:</span>
                  <strong style={{ color: "var(--text-primary)", fontSize: "15px" }}>{total.toLocaleString("vi-VN")}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Số Lượng Nhãn (Items):</span>
                  <strong style={{ color: "var(--text-primary)", fontSize: "15px" }}>{(data || []).length.toLocaleString("vi-VN")}</strong>
                </div>
              </div>
              <div style={{ width: "1px", height: "80%", background: "var(--border)", opacity: 0.5 }}></div>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "14px", color: "var(--text-secondary)", position: "relative", top: "2px" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Mức Trung Bình:</span>
                  <strong style={{ color: "var(--text-primary)", fontSize: "15px" }}>{avg.toLocaleString("vi-VN")}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <span>Giá Trị Kịch Trần (Max):</span>
                  <div style={{ textAlign: "right" }}>
                    <strong style={{ color: "var(--text-primary)", fontSize: "15px" }}>{max.toLocaleString("vi-VN")}</strong>
                    <br />
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px", display: "inline-block" }}>(Đỉnh điểm)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div style={{ padding: "16px 24px", display: "flex", justifyContent: "flex-end", backgroundColor: "#f9fafb", borderBottomLeftRadius: "16px", borderBottomRightRadius: "16px", borderTop: "1px solid #e5e7eb" }}>
            <button onClick={handleClose} className="btn-primary" style={{ padding: "8px 24px", borderRadius: "6px", fontSize: "14px", fontWeight: "600" }}>
              Đóng
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

function ChartCard({ title, subtitle, points = [], type = "area", accent = "#a78bfa", icon: Icon, onClick }) {
  return (
    <div className="panel chart-card-panel">
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div className="title-with-icon">
          {Icon && <Icon size={18} className="text-secondary" />}
          <div>
            <h3>{title}</h3>
            {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
          </div>
        </div>
        {onClick && (
          <button
            className="btn-outline"
            onClick={onClick}
            style={{ padding: '4px 10px', fontSize: '0.8rem' }}
          >
            Chi tiết
          </button>
        )}
      </div>
      <div className="chart-body">
        {points.length === 0 ? (
          <p className="empty-state">Chưa có dữ liệu cho biểu đồ này.</p>
        ) : type === "donut" ? (
          <DonutChart points={points} />
        ) : type === "bar" ? (
          <BarChart points={points} color={accent} />
        ) : (
          <AreaChart points={points} color={accent} />
        )}
      </div>
    </div>
  );
}

function MetricCollection({ title, subtitle, metrics = [], icon: Icon }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="title-with-icon">
          {Icon && <Icon size={18} className="text-secondary" />}
          <div>
            <h3>{title}</h3>
            {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
          </div>
        </div>
      </div>

      <div className="mini-metric-grid">
        {metrics.map((metric) => (
          <div key={`${title}-${metric.label}`} className="mini-metric-card">
            <span>{metric.label}</span>
            <strong>{formatMetricValue(metric)}</strong>
            {metric.detail ? <p>{metric.detail}</p> : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function InsightTable({ title, subtitle, columns, rows = [], icon: Icon }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="title-with-icon">
          {Icon && <Icon size={18} className="text-secondary" />}
          <div>
            <h3>{title}</h3>
            {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
          </div>
        </div>
      </div>

      {rows.length === 0 ? (
        <p className="empty-state">Chưa có dữ liệu để hiển thị.</p>
      ) : (
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={`${title}-${column.key}`}>{column.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${title}-${index}-${row.label || row.email || row.created_at || "row"}`}>
                  {columns.map((column) => (
                    <td key={`${title}-${index}-${column.key}`}>
                      {column.render ? column.render(row[column.key], row) : row[column.key] ?? "--"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function AdminConsole() {
  const router = useRouter();
  const { session, setSession, booting } = useSessionGuard({
    mode: "protected",
    requireAdmin: true,
    fallbackPath: "/",
  });
  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeSection, setActiveSection] = useState("overview");
  const [drillDown, setDrillDown] = useState(null);

  useEffect(() => {
    if (booting) {
      return;
    }

    if (session?.token) {
      loadAdminData(session.token);
    } else {
      setLoading(false);
    }
  }, [booting, session]);

  const summaryMetrics = useMemo(() => analytics?.overview || [], [analytics]);
  const systemMetrics = useMemo(() => analytics?.system_metrics || [], [analytics]);
  const modelMetrics = useMemo(() => analytics?.model_metrics || [], [analytics]);
  const dataMetrics = useMemo(() => analytics?.data_metrics || [], [analytics]);
  const charts = useMemo(() => analytics?.charts || {}, [analytics]);
  const tables = useMemo(() => analytics?.tables || {}, [analytics]);

  async function loadAdminData(token) {
    setLoading(true);
    setError("");
    try {
      const [userRows, logRows, analyticsPayload] = await Promise.all([
        listUsers(token),
        listLogs(token),
        getAdminAnalytics(token),
      ]);
      setUsers(userRows);
      setLogs(logRows);
      setAnalytics(analyticsPayload);
    } catch (requestError) {
      setError(requestError.message || "Không thể tải dữ liệu admin.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRoleChange(userId, role) {
    if (!session?.token) {
      return;
    }
    try {
      await updateUserRole(session.token, userId, role);
      await loadAdminData(session.token);
    } catch (requestError) {
      setError(requestError.message || "Không thể cập nhật role.");
    }
  }

  function handleLogout() {
    clearStoredSession();
    setSession(null);
    router.replace("/login");
    router.refresh();
  }

  if (booting) {
    return (
      <main className="auth-redirect-shell">
        <section className="auth-redirect-card">
          <div className="logo-area">
            <div className="logo-icon">SV</div>
            <h2>SummVi Admin</h2>
          </div>
          <h1>Đang khởi tạo dashboard admin.</h1>
          <p>Đang đồng bộ session và lấy analytics từ backend.</p>
        </section>
      </main>
    );
  }

  if (!session?.token) {
    return (
      <main className="auth-redirect-shell">
        <section className="auth-redirect-card">
          <div className="logo-area">
            <div className="logo-icon">SV</div>
            <h2>SummVi Admin</h2>
          </div>
          <h1>Cần đăng nhập bằng tài khoản admin.</h1>
          <p>Sử dụng admin mặc định hoặc một tài khoản đã được nâng role để vào dashboard này.</p>
          <div className="hero-links">
            <Link href="/login">Đăng nhập</Link>
            <Link href="/">Workspace</Link>
          </div>
        </section>
      </main>
    );
  }

  if (!isAdminSession(session)) {
    return (
      <main className="auth-redirect-shell">
        <section className="auth-redirect-card">
          <div className="logo-area">
            <div className="logo-icon">SV</div>
            <h2>SummVi Admin</h2>
          </div>
          <h1>Role hiện tại không đủ quyền.</h1>
          <p>Bạn đang đăng nhập với role {session.role}. Cần admin role để xem users và system logs.</p>
          <div className="hero-links">
            <Link href="/">Workspace</Link>
            <button onClick={handleLogout} type="button">
              Đăng xuất
            </button>
          </div>
        </section>
      </main>
    );
  }

  const sectionTitle =
    NAV_ITEMS.find((item) => item.id === activeSection)?.label || "Bảng điều khiển hệ thống";

  return (
    <div className="app-container">
      <aside className="sidebar admin-sidebar">
        <div
          className="logo-area"
          onClick={() => router.push("/")}
          style={{ cursor: "pointer" }}
        >
          <div className="logo-icon admin-icon">AD</div>
          <h2>
            SummVi <span className="badge">Admin</span>
          </h2>
        </div>


        <div className="user-profile admin-profile">
          <div className="avatar">{session.email.slice(0, 2).toUpperCase()}</div>
          <div className="user-info">
            <p className="user-name">{session.email}</p>
            <p className="user-plan text-danger">Quản trị viên hệ thống</p>
          </div>
          <Link className="settings-icon" href="/">
            {"->"}
          </Link>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            <h2>{sectionTitle}</h2>
          </div>
          <div className="admin-top-nav">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                className={`top-nav-item ${activeSection === item.id ? "active" : ""}`}
                onClick={() => setActiveSection(item.id)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="topbar-actions">
            <button className="btn-outline" onClick={() => loadAdminData(session.token)} type="button">
              <RefreshCcw size={14} className="mr-2" /> Làm mới
            </button>
            <div className="status-indicator">
              <span className="dot pulse" />
              <span>{loading ? "Đang đồng bộ dữ liệu" : "Đã đồng bộ analytics"}</span>
            </div>
          </div>
        </header>

        <div className="workspace admin-workspace">
          {error ? <p className="inline-error">{error}</p> : null}

          {activeSection === "overview" ? (
            <section className="section-stack">
              <div className="stats-grid">
                {summaryMetrics.map((metric, idx) => {
                  const chartData = idx === 0 ? charts.request_volume : idx === 3 ? charts.error_volume : [];
                  return (
                    <div key={metric.label} className="stat-card">
                      <div className="stat-header">
                        <div className="stat-icon b-purple"><TrendingUp size={16} /></div>
                        <Sparkline points={chartData} color={idx === 3 ? "#f87171" : "#a78bfa"} />
                      </div>
                      <h3>{formatMetricValue(metric)}</h3>
                      <p>{metric.label}</p>
                      <span className="panel-subtitle">{metric.detail}</span>
                    </div>
                  );
                })}
              </div>

              <div className="chart-grid chart-grid-2">
                <ChartCard
                  accent="#a78bfa"
                  icon={Activity}
                  points={charts.request_volume}
                  subtitle="Tổng request hệ thống theo ngày"
                  title="Lưu lượng Request"
                  onClick={() => setDrillDown({ title: "Lưu lượng Request", data: charts.request_volume, type: "area", accent: "#a78bfa" })}
                />
                <ChartCard
                  accent="#f87171"
                  icon={AlertCircle}
                  points={charts.error_volume}
                  subtitle="Số request lỗi ghi nhận theo ngày"
                  title="Tỷ lệ Lỗi"
                  onClick={() => setDrillDown({ title: "Tỷ lệ Lỗi", data: charts.error_volume, type: "area", accent: "#f87171" })}
                />
                <ChartCard
                  type="donut"
                  icon={Database}
                  points={charts.endpoint_distribution}
                  subtitle="Các endpoint có lưu lượng cao"
                  title="Phân bổ Endpoint"
                  onClick={() => setDrillDown({ title: "Phân bổ Endpoint", data: charts.endpoint_distribution, type: "donut" })}
                />
                <ChartCard
                  type="donut"
                  icon={ShieldCheck}
                  points={charts.status_distribution}
                  subtitle="Phân bổ trạng thái phản hồi HTTP"
                  title="Trạng thái Phản hồi"
                  onClick={() => setDrillDown({ title: "Trạng thái Phản hồi", data: charts.status_distribution, type: "donut" })}
                />
              </div>

              <div className="chart-grid chart-grid-3">
                <MetricCollection icon={Settings} metrics={systemMetrics} subtitle="Chỉ số vận hành API và ứng dụng" title="Hệ thống" />
                <MetricCollection icon={BarChart3} metrics={modelMetrics} subtitle="Chỉ số inference và chất lượng model" title="Model AI" />
                <MetricCollection icon={Database} metrics={dataMetrics} subtitle="Chỉ số dữ liệu và feedback" title="Dữ liệu & RAG" />
              </div>
            </section>
          ) : null}

          {activeSection === "users" ? (
            <section className="section-stack">
              <div className="chart-grid chart-grid-2">
                <ChartCard
                  accent="#3b82f6"
                  icon={Users}
                  points={charts.user_growth}
                  subtitle="Người dùng mới tham gia theo ngày"
                  title="Tăng trưởng Người dùng"
                  onClick={() => setDrillDown({ title: "Chi tiết Tăng trưởng", data: charts.user_growth })}
                />
                <ChartCard
                  type="donut"
                  icon={Activity}
                  points={tables.activity_leaders?.map((row) => ({ label: row.label, value: row.value })) || []}
                  subtitle="Người dùng có nhiều hành động nhất"
                  title="Người dùng Tích cực"
                  onClick={() => setDrillDown({ title: "Top User Hoạt động", data: tables.activity_leaders })}
                />
              </div>

              <InsightTable
                icon={TrendingUp}
                columns={[
                  { key: "label", label: "Khoảng thời gian" },
                  { key: "value", label: "Tỷ lệ giữ chân (%)", render: (value) => <strong>{value}%</strong> },
                  { key: "tertiary", label: "Số lượng User" },
                ]}
                rows={tables.retention || []}
                subtitle="Phân tích mức độ quay lại của người dùng"
                title="Tỷ lệ Giữ chân (Retention)"
              />

              <InsightTable
                icon={ShieldCheck}
                columns={[
                  { key: "email", label: "Email", render: (value) => <code>{value}</code> },
                  { key: "role", label: "Quyền hạn" },
                  {
                    key: "is_active",
                    label: "Trạng thái",
                    render: (value) => (
                      <span className={`status-badge ${value ? "success" : "error"}`}>
                        {value ? "Hoạt động" : "Khóa"}
                      </span>
                    ),
                  },
                  { key: "created_at", label: "Ngày tham gia", render: (value) => formatDate(value) },
                  {
                    key: "id",
                    label: "Thao tác",
                    render: (_value, row) => (
                      <div className="action-cell">
                        <button
                          className="btn-outline"
                          disabled={row.role === "admin"}
                          onClick={() => handleRoleChange(row.id, "admin")}
                          type="button"
                        >
                          Cấp Admin
                        </button>
                        <button
                          className="btn-outline"
                          disabled={row.role === "user"}
                          onClick={() => handleRoleChange(row.id, "user")}
                          type="button"
                        >
                          Gỡ quyền
                        </button>
                      </div>
                    ),
                  },
                ]}
                rows={users}
                subtitle="Danh sách người dùng và phân quyền"
                title="Quản lý Người dùng"
              />
            </section>
          ) : null}

          {activeSection === "logs" ? (
            <section className="section-stack">
              <div className="chart-grid chart-grid-2">
                <ChartCard
                  accent="#a78bfa"
                  icon={Activity}
                  points={charts.hourly_volume || charts.request_volume}
                  subtitle={charts.hourly_volume ? "Lưu lượng tính theo khung giờ gần nhất" : "Xu hướng request trong 7 ngày gần nhất"}
                  title="Xu hướng Request"
                  onClick={() => setDrillDown({ title: "Chi tiết Lưu lượng Request", data: charts.hourly_volume || charts.request_volume, type: "area", accent: "#a78bfa" })}
                />
                <ChartCard
                  accent="#f59e0b"
                  icon={TrendingUp}
                  points={charts.latency_trend}
                  subtitle="Độ trễ trung bình của hệ thống theo ngày"
                  title="Xu hướng Độ trễ"
                  onClick={() => setDrillDown({ title: "Chi tiết Độ trễ", data: charts.latency_trend, type: "area", accent: "#f59e0b" })}
                />
                <ChartCard
                  type="donut"
                  icon={CheckCircle}
                  points={charts.endpoint_distribution}
                  subtitle="Các endpoint được gọi nhiều nhất"
                  title="Lưu lượng Endpoint"
                  onClick={() => setDrillDown({ title: "Phân bổ Endpoint", data: charts.endpoint_distribution, type: "donut" })}
                />
                <ChartCard
                  type="donut"
                  icon={AlertCircle}
                  points={tables.top_endpoints?.map((row) => ({ label: row.label, value: row.value })) || []}
                  subtitle="Thống kê tải theo từng endpoint"
                  title="Top Endpoints"
                  onClick={() => setDrillDown({ title: "Top Endpoints", data: tables.top_endpoints, type: "donut" })}
                />
              </div>

              <InsightTable
                icon={Activity}
                columns={[
                  {
                    key: "status_code",
                    label: "Trạng thái",
                    render: (value) => (
                      <span className={`status-badge ${Number(value) < 400 ? "success" : "error"}`}>{value}</span>
                    ),
                  },
                  { key: "endpoint", label: "Endpoint", render: (value) => <code>{value}</code> },
                  { key: "method", label: "Phương thức" },
                  { key: "response_time", label: "Độ trễ", render: (value) => `${value ?? "--"}ms` },
                  { key: "user_id", label: "Người dùng", render: (value) => value || "vô danh" },
                  { key: "created_at", label: "Thời gian", render: (value) => formatDate(value) },
                ]}
                rows={logs.slice(0, 20)}
                subtitle="Nhật ký hệ thống gần đây"
                title="Logs và Hiệu suất"
              />

              <InsightTable
                icon={AlertCircle}
                columns={[
                  { key: "label", label: "Endpoint", render: (value) => <code>{value}</code> },
                  { key: "value", label: "Mã lỗi" },
                  { key: "secondary", label: "Loại lỗi" },
                  { key: "tertiary", label: "Thông báo" },
                  { key: "created_at", label: "Thời gian", render: (value) => formatDate(value) },
                ]}
                rows={tables.recent_errors || []}
                subtitle="Danh sách các lỗi mới nhất để xử lý nhanh"
                title="Lỗi Gần đây"
              />
            </section>
          ) : null}

          {activeSection === "model" ? (
            <section className="section-stack">
              <MetricCollection icon={BarChart3} metrics={modelMetrics} subtitle="Chỉ số phản ánh độ ổn định của trí tuệ nhân tạo" title="Sức khỏe Model AI" />

              <div className="chart-grid chart-grid-2">
                <ChartCard
                  accent="#a78bfa"
                  icon={Activity}
                  points={charts.inference_volume}
                  subtitle="Số lượt model thực hiện tóm tắt theo ngày"
                  title="Lưu lượng Inference"
                  onClick={() => setDrillDown({ title: "Lưu lượng Inference", data: charts.inference_volume, type: "area", accent: "#a78bfa" })}
                />
                <ChartCard
                  accent="#10b981"
                  icon={TrendingUp}
                  points={charts.compression_trend}
                  subtitle="Tỷ lệ nén văn bản trung bình ghi nhận"
                  title="Xu hướng Nén văn bản"
                  onClick={() => setDrillDown({ title: "Xu hướng Nén văn bản", data: charts.compression_trend, type: "area", accent: "#10b981" })}
                />
                <ChartCard
                  type="donut"
                  icon={Settings}
                  points={charts.stage_latency_breakdown}
                  subtitle="Phân bố độ trễ theo từng giai đoạn xử lý"
                  title="Phân tách quy trình"
                  onClick={() => setDrillDown({ title: "Phân tách quy trình", data: charts.stage_latency_breakdown, type: "donut" })}
                />
                <ChartCard
                  type="donut"
                  icon={Database}
                  points={charts.backend_distribution}
                  subtitle="Các backend đang phục vụ tóm tắt"
                  title="Phân bổ Backend"
                  onClick={() => setDrillDown({ title: "Phân bổ Backend", data: charts.backend_distribution, type: "donut" })}
                />
                <ChartCard
                  type="donut"
                  icon={ShieldCheck}
                  points={charts.device_distribution}
                  subtitle="Phần cứng đang vận hành model (CPU/GPU)"
                  title="Thiết bị Vận hành"
                  onClick={() => setDrillDown({ title: "Thiết bị Vận hành", data: charts.device_distribution, type: "donut" })}
                />
              </div>

              <InsightTable
                icon={BarChart3}
                columns={[
                  { key: "label", label: "Model / Backend" },
                  { key: "value", label: "Độ trễ (s)" },
                  { key: "secondary", label: "Tỷ lệ nén" },
                  { key: "tertiary", label: "Thiết bị" },
                  { key: "created_at", label: "Thời gian", render: (value) => formatDate(value) },
                ]}
                rows={tables.recent_inference || []}
                subtitle="Các bản ghi xử lý AI mới nhất"
                title="Nhật ký Inference mới nhất"
              />
            </section>
          ) : null}

          {activeSection === "data" ? (
            <section className="section-stack">
              <MetricCollection icon={Database} metrics={dataMetrics} subtitle="Chỉ số phản ánh sức khỏe kho dữ liệu vector" title="Dữ liệu & RAG" />

              <div className="chart-grid chart-grid-2">
                <ChartCard
                  accent="#3b82f6"
                  icon={TrendingUp}
                  points={charts.chunk_trend}
                  subtitle="Số lượng chunk được trích xuất từ tài liệu"
                  title="Xu hướng Chunk RAG"
                  onClick={() => setDrillDown({ title: "Xu hướng Chunk RAG", data: charts.chunk_trend, type: "area", accent: "#3b82f6" })}
                />
                <ChartCard
                  type="donut"
                  icon={Activity}
                  points={charts.activity_distribution}
                  subtitle="Các hành động chính của người dùng"
                  title="Phân bổ Hành động"
                  onClick={() => setDrillDown({ title: "Phân bổ Hành động", data: charts.activity_distribution, type: "donut" })}
                />
                <ChartCard
                  type="donut"
                  icon={AlertCircle}
                  points={charts.rating_distribution}
                  subtitle="Phản hồi từ người dùng về chất lượng"
                  title="Phân bổ Đánh giá"
                  onClick={() => setDrillDown({ title: "Phân bổ Đánh giá", data: charts.rating_distribution, type: "donut" })}
                />
                <ChartCard
                  accent="#10b981"
                  icon={Users}
                  points={charts.user_growth}
                  subtitle="Đối chiếu tăng trưởng người dùng và dữ liệu"
                  title="Tương quan Người dùng"
                  onClick={() => setDrillDown({ title: "Tương quan Người dùng", data: charts.user_growth, type: "area", accent: "#10b981" })}
                />
              </div>

              <div className="chart-grid chart-grid-2">
                <ChartCard
                  type="bar"
                  accent="#8b5cf6"
                  icon={BarChart3}
                  points={charts.length_histogram || []}
                  subtitle="Phân phối độ dài của văn bản đầu vào"
                  title="Phân phối Độ dài Đầu vào"
                  onClick={() => setDrillDown({ title: "Dữ liệu Phân phối Độ dài", data: charts.length_histogram, type: "bar", accent: "#8b5cf6" })}
                />
              </div>

              <InsightTable
                icon={Database}
                columns={[
                  { key: "label", label: "Nội dung", render: (value) => <code>{value}</code> },
                  { key: "value", label: "Số lần trùng lặp", render: (value) => <strong>{value}</strong> },
                ]}
                rows={(tables.top_inputs || []).slice(0, 20)}
                subtitle="Các văn bản được gửi lên nhiều nhất"
                title="Top Truy vấn Trùng lặp"
              />

              <InsightTable
                icon={Users}
                columns={[
                  { key: "email", label: "Email", render: (value) => <code>{value}</code> },
                  {
                    key: "rating",
                    label: "Đánh giá",
                    render: (value) => (
                      <span style={{ color: value >= 4 ? "#10b981" : value >= 3 ? "#f59e0b" : "#ef4444", fontWeight: 600 }}>
                        {"★".repeat(value)}{"☆".repeat(5 - value)}
                      </span>
                    ),
                  },
                  { key: "feedback", label: "Phản hồi" },
                  { key: "created_at", label: "Thời gian", render: (value) => formatDate(value) },
                ]}
                rows={(tables.ratings_detail || []).slice(0, 20)}
                subtitle="Chi tiết đánh giá chất lượng tóm tắt từ người dùng"
                title="Chi tiết Đánh giá Người dùng"
              />
            </section>
          ) : null}
        </div>
      </main>
      {drillDown && (
        <DrillDownModal
          title={drillDown.title}
          data={drillDown.data}
          type={drillDown.type}
          accent={drillDown.accent}
          onClose={() => setDrillDown(null)}
        />
      )}
    </div>
  );
}
