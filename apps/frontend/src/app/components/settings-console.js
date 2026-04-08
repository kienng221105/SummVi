"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { clearStoredSession, isAdminSession } from "../lib/session";
import { useSessionGuard } from "../lib/session-guard";

function getInitials(email) {
  if (!email) {
    return "SV";
  }
  const localPart = email.split("@")[0] || email;
  return localPart.slice(0, 2).toUpperCase();
}

export default function SettingsConsole() {
  const router = useRouter();
  const { session, setSession, booting } = useSessionGuard({ mode: "protected" });

  function handleLogout() {
    clearStoredSession();
    setSession(null);
    router.replace("/login");
    router.refresh();
  }

  const adminSession = isAdminSession(session);

  if (booting) {
    return (
      <main className="auth-redirect-shell">
        <section className="auth-redirect-card">
          <div className="logo-area">
            <div className="logo-icon">SV</div>
            <h2>SummVi</h2>
          </div>
          <h1>Đang tải hồ sơ cá nhân.</h1>
          <p>Đồng bộ session và kiểm tra quyền truy cập.</p>
        </section>
      </main>
    );
  }

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="logo-area">
          <div className="logo-icon">SV</div>
          <h2>SummVi</h2>
        </div>

        <Link className="nav-link-btn" href="/">
          <button className="new-chat-btn" type="button">
            Về workspace
          </button>
        </Link>

        <div className="settings-nav">
          <p className="section-title">Tài khoản</p>
          <ul className="history-list">
            <li className="history-item active">Hồ sơ cá nhân</li>
            {adminSession ? (
              <li className="history-item">
                <Link href="/admin">Quản trị hệ thống</Link>
              </li>
            ) : null}
          </ul>
        </div>

        <div className="nav-section spacer-section" />

        <button className="user-profile logout-profile" onClick={handleLogout} type="button">
          <div className="user-info">
            <p className="user-name logout-name">Đăng xuất</p>
          </div>
        </button>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            <h2>Hồ sơ cá nhân</h2>
          </div>
        </header>

        <div className="workspace settings-workspace">
          <div className="settings-card">
            <div className="profile-header">
              <div className="profile-avatar">{getInitials(session?.email)}</div>
              <div className="profile-actions">
                <h3>Thông tin tài khoản</h3>
              </div>
            </div>

            <hr className="separator" />

            <div className="form-section-title">
              <h3>Dữ liệu tài khoản</h3>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Email</label>
                <input readOnly type="text" value={session?.email || "Chưa đăng nhập"} />
              </div>
              <div className="form-group">
                <label>Role</label>
                <input readOnly type="text" value={session?.role || "--"} />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>User ID</label>
                <input readOnly type="text" value={session?.userId || "--"} />
              </div>
              <div className="form-group">
                <label>Trạng thái</label>
                <input readOnly type="text" value={session?.isActive === false ? "Tạm khóa" : "Đang hoạt động"} />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
