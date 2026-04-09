"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

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
  { id: "overview", label: "Tổng quan" },
  { id: "users", label: "Quản lý người dùng" },
  { id: "logs", label: "Logs và hiệu suất" },
  { id: "model", label: "Giám sát model" },
  { id: "data", label: "Dữ liệu và RAG" },
];

function formatDate(value) {
  if (!value) {
    return "--";
  }
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatMetricValue(metric) {
  if (!metric) {
    return "--";
  }
  return `${metric.value}${metric.unit || ""}`;
}

function ChartCard({ title, subtitle, points = [], mode = "vertical", accent = "b-purple" }) {
  const maxValue = Math.max(...points.map((point) => Number(point.value) || 0), 1);

  return (
    <div className="panel chart-card-panel">
      <div className="panel-header">
        <div>
          <h3>{title}</h3>
          {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
        </div>
      </div>

      {points.length === 0 ? (
        <p className="empty-state">Chưa có dữ liệu cho biểu đồ này.</p>
      ) : mode === "horizontal" ? (
        <div className="horizontal-chart">
          {points.map((point) => (
            <div key={`${title}-${point.label}`} className="hbar-row">
              <div className="hbar-label-row">
                <span>{point.label}</span>
                <strong>{point.value}</strong>
              </div>
              <div className="hbar-track">
                <div
                  className={`hbar-fill ${accent}`}
                  style={{ width: `${Math.max((Number(point.value) / maxValue) * 100, 4)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mock-chart">
          {points.map((point) => (
            <div key={`${title}-${point.label}`} className="bar-col wide">
              <div
                className={`bar ${accent}`}
                style={{ height: `${Math.max((Number(point.value) / maxValue) * 100, 8)}%` }}
              />
              <span className="label">{point.label}</span>
              <span className="chart-value">{point.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MetricCollection({ title, subtitle, metrics = [] }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h3>{title}</h3>
          {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
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

function InsightTable({ title, subtitle, columns, rows = [] }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h3>{title}</h3>
          {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
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
      setError(requestError.message || "Khong the tai du lieu admin.");
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
      setError(requestError.message || "Khong the cap nhat role.");
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
        <div className="logo-area">
          <div className="logo-icon admin-icon">AD</div>
          <h2>
            SummVi <span className="badge">Admin</span>
          </h2>
        </div>

        <div className="admin-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${activeSection === item.id ? "active" : ""}`}
              onClick={() => setActiveSection(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
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
          <div className="topbar-actions">
            <button className="btn-outline" onClick={() => loadAdminData(session.token)} type="button">
              Lam moi
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
                {summaryMetrics.map((metric) => (
                  <div key={metric.label} className="stat-card">
                    <div className="stat-header">
                      <div className="stat-icon b-purple">KPI</div>
                      <span className="trend positive">{metric.detail || "Overview"}</span>
                    </div>
                    <h3>{formatMetricValue(metric)}</h3>
                    <p>{metric.label}</p>
                  </div>
                ))}
              </div>

              <div className="chart-grid chart-grid-2">
                <ChartCard
                  accent="b-purple"
                  points={charts.request_volume}
                  subtitle="Tổng request system theo ngày"
                  title="Lưu lượng request"
                />
                <ChartCard
                  accent="b-orange"
                  points={charts.error_volume}
                  subtitle="Số request lỗi theo ngày"
                  title="Lưu lượng lỗi"
                />
                <ChartCard
                  accent="b-blue"
                  mode="horizontal"
                  points={charts.endpoint_distribution}
                  subtitle="Top endpoint có lưu lượng cao"
                  title="Phân bố endpoint"
                />
                <ChartCard
                  accent="b-green"
                  mode="horizontal"
                  points={charts.status_distribution}
                  subtitle="Phan bo trang thai HTTP"
                  title="Phân bố trạng thái"
                />
              </div>

              <div className="chart-grid chart-grid-3">
                <MetricCollection metrics={systemMetrics} subtitle="Chỉ số vận hành API và app" title="System metrics" />
                <MetricCollection metrics={modelMetrics} subtitle="Chỉ số inference và chất lượng model" title="Model metrics" />
                <MetricCollection metrics={dataMetrics} subtitle="Chỉ số dữ liệu, feedback và chunking" title="Data metrics" />
              </div>
            </section>
          ) : null}

          {activeSection === "users" ? (
            <section className="section-stack">
              <div className="chart-grid chart-grid-2">
                <ChartCard
                  accent="b-blue"
                  points={charts.user_growth}
                  subtitle="User mới theo ngày"
                  title="Tăng trưởng user"
                />
                <ChartCard
                  accent="b-purple"
                  mode="horizontal"
                  points={tables.activity_leaders?.map((row) => ({ label: row.label, value: row.value })) || []}
                  subtitle="Top user co nhieu hanh dong nhat"
                  title="Activity leaders"
                />
              </div>

              <InsightTable
                columns={[
                  { key: "email", label: "Email", render: (value) => <code>{value}</code> },
                  { key: "role", label: "Role" },
                  {
                    key: "is_active",
                    label: "Status",
                    render: (value) => (
                      <span className={`status-badge ${value ? "success" : "error"}`}>
                        {value ? "active" : "inactive"}
                      </span>
                    ),
                  },
                  { key: "created_at", label: "Created", render: (value) => formatDate(value) },
                  {
                    key: "id",
                    label: "Action",
                    render: (_value, row) => (
                      <div className="action-cell">
                        <button
                          className="btn-outline"
                          disabled={row.role === "admin"}
                          onClick={() => handleRoleChange(row.id, "admin")}
                          type="button"
                        >
                          Make admin
                        </button>
                        <button
                          className="btn-outline"
                          disabled={row.role === "user"}
                          onClick={() => handleRoleChange(row.id, "user")}
                          type="button"
                        >
                          Set user
                        </button>
                      </div>
                    ),
                  },
                ]}
                rows={users}
                subtitle="Danh sach user va thao tac role"
                title="Quản lý người dùng"
              />
            </section>
          ) : null}

          {activeSection === "logs" ? (
            <section className="section-stack">
              <div className="chart-grid chart-grid-2">
                <ChartCard
                  accent="b-purple"
                  points={charts.request_volume}
                  subtitle="Tổng request 7 ngày"
                  title="Request trend"
                />
                <ChartCard
                  accent="b-orange"
                  points={charts.latency_trend}
                  subtitle="Latency trung bình theo ngày"
                  title="Latency trend"
                />
                <ChartCard
                  accent="b-green"
                  mode="horizontal"
                  points={charts.endpoint_distribution}
                  subtitle="Top endpoint duoc goi nhieu nhat"
                  title="Endpoint traffic"
                />
                <ChartCard
                  accent="b-blue"
                  mode="horizontal"
                  points={tables.top_endpoints?.map((row) => ({ label: row.label, value: row.value })) || []}
                  subtitle="Top endpoint theo luong request"
                  title="Top endpoints"
                />
              </div>

              <InsightTable
                columns={[
                  {
                    key: "status_code",
                    label: "Status",
                    render: (value) => (
                      <span className={`status-badge ${Number(value) < 400 ? "success" : "error"}`}>{value}</span>
                    ),
                  },
                  { key: "endpoint", label: "Endpoint", render: (value) => <code>{value}</code> },
                  { key: "method", label: "Method" },
                  { key: "response_time", label: "Latency", render: (value) => `${value ?? "--"}ms` },
                  { key: "user_id", label: "User", render: (value) => value || "anonymous" },
                  { key: "created_at", label: "Thời gian", render: (value) => formatDate(value) },
                ]}
                rows={logs}
                subtitle="System logs gần nhất"
                title="Logs và hiệu suất"
              />

              <InsightTable
                columns={[
                  { key: "label", label: "Endpoint", render: (value) => <code>{value}</code> },
                  { key: "value", label: "Status" },
                  { key: "secondary", label: "Error type" },
                  { key: "tertiary", label: "Message" },
                  { key: "created_at", label: "Thoi gian", render: (value) => formatDate(value) },
                ]}
                rows={tables.recent_errors || []}
                subtitle="Lỗi gần nhất để debug nhanh"
                title="Lỗi gần nhất"
              />
            </section>
          ) : null}

          {activeSection === "model" ? (
            <section className="section-stack">
              <MetricCollection metrics={modelMetrics} subtitle="Chỉ số tổng quan của model" title="Sức khỏe model" />

              <div className="chart-grid chart-grid-2">
                <ChartCard
                  accent="b-purple"
                  points={charts.inference_volume}
                  subtitle="So request inference theo ngay"
                  title="Lưu lượng inference"
                />
                <ChartCard
                  accent="b-green"
                  points={charts.compression_trend}
                  subtitle="Compression ratio trung binh theo ngay"
                  title="Xu hướng compression"
                />
                <ChartCard
                  accent="b-orange"
                  mode="horizontal"
                  points={charts.stage_latency_breakdown}
                  subtitle="Độ trễ trung bình theo stage"
                  title="Phân rã độ trễ theo stage"
                />
                <ChartCard
                  accent="b-blue"
                  mode="horizontal"
                  points={charts.backend_distribution}
                  subtitle="Backend generation hiện đang phục vụ"
                  title="Backend sinh summary"
                />
                <ChartCard
                  accent="b-green"
                  mode="horizontal"
                  points={charts.device_distribution}
                  subtitle="Model đang chạy trên thiết bị nào"
                  title="Phân bố thiết bị"
                />
                <ChartCard
                  accent="b-purple"
                  mode="horizontal"
                  points={tables.recent_inference?.map((row) => ({ label: row.label, value: row.value })) || []}
                  subtitle="Độ trễ của các inference gần nhất"
                  title="Độ trễ inference gần nhất"
                />
              </div>

              <InsightTable
                columns={[
                  { key: "label", label: "Model / backend" },
                  { key: "value", label: "Latency (s)" },
                  { key: "secondary", label: "Compression" },
                  { key: "tertiary", label: "Device" },
                  { key: "created_at", label: "Thời gian", render: (value) => formatDate(value) },
                ]}
                rows={tables.recent_inference || []}
                subtitle="Bản ghi inference mới nhất"
                title="Bản ghi inference gần nhất"
              />
            </section>
          ) : null}

          {activeSection === "data" ? (
            <section className="section-stack">
              <MetricCollection metrics={dataMetrics} subtitle="Chỉ số dữ liệu, chunking và feedback" title="Sức khỏe dữ liệu và RAG" />

              <div className="chart-grid chart-grid-2">
                <ChartCard
                  accent="b-blue"
                  points={charts.chunk_trend}
                  subtitle="Retrieved chunks trung bình theo ngày"
                  title="Xu hướng chunk RAG"
                />
                <ChartCard
                  accent="b-purple"
                  mode="horizontal"
                  points={charts.activity_distribution}
                  subtitle="Phân bố action của user"
                  title="Phân bố hoạt động user"
                />
                <ChartCard
                  accent="b-orange"
                  mode="horizontal"
                  points={charts.rating_distribution}
                  subtitle="Phân bố feedback rating"
                  title="Phân bố rating"
                />
                <ChartCard
                  accent="b-green"
                  points={charts.user_growth}
                  subtitle="Tăng trưởng người dùng để đối chiếu với data volume"
                  title="Tăng trưởng user so với tải dữ liệu"
                />
              </div>

              <InsightTable
                columns={[
                  { key: "label", label: "Endpoint / User" },
                  { key: "value", label: "Giá trị" },
                  { key: "secondary", label: "Thông tin thêm" },
                  { key: "status", label: "Status" },
                ]}
                rows={tables.top_endpoints || []}
                subtitle="Bảng đối chiếu traffic và nghiêng tải tài nguyên"
                title="Phân tích vận hành chi tiết"
              />
            </section>
          ) : null}
        </div>
      </main>
    </div>
  );
}
