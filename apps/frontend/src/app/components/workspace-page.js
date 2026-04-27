"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  deleteConversation,
  getConversationMessages,
  getConversationRating,
  listConversations,
  summarizeLegacy,
  summarizeText,
  uploadDocument,
  upsertRating,
} from "../lib/api";
import { clearStoredSession } from "../lib/session";
import { useSessionGuard } from "../lib/session-guard";

const QUICK_START_TEXT =
  "Nhập một đoạn văn tiếng Việt để tạo tóm tắt.";

const LENGTH_OPTIONS = [
  { label: "Ngắn", value: "short" },
  { label: "Vừa", value: "medium" },
  { label: "Chi tiết", value: "long" },
];

const STAR_VALUES = [1, 2, 3, 4, 5];

function formatDate(value) {
  if (!value) {
    return "--";
  }
  const normalized = typeof value === "string" && !value.endsWith("Z") && !value.includes("+") ? value + "Z" : value;
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(normalized));
}

function getInitials(email) {
  if (!email) {
    return "SV";
  }
  return email.slice(0, 2).toUpperCase();
}

function splitSummary(summary) {
  /**
   * Tách summary thành các bullet points để render dạng list.
   *
   * Logic:
   * - Split theo newline hoặc sau dấu câu (. ! ?)
   * - Regex lookbehind (?<=...) để giữ dấu câu trong kết quả
   * - Filter bỏ empty strings
   */
  if (!summary) {
    return [];
  }

  return summary
    .split(/\n+|(?<=[.!?])\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function countWords(text) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

export default function WorkspacePage() {
  const router = useRouter();
  const { session, setSession, booting } = useSessionGuard({ mode: "protected" });
  const hydrateRequestIdRef = useRef(0);
  const [activeView, setActiveView] = useState("composer"); // composer | history
  const [activeTab, setActiveTab] = useState("text");
  const [text, setText] = useState("");
  const [conversationTitle, setConversationTitle] = useState("");
  const [summaryLength, setSummaryLength] = useState("medium");
  const [outputFormat, setOutputFormat] = useState("bullet");
  const [conversations, setConversations] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState("");
  const [messages, setMessages] = useState([]);
  const [currentRating, setCurrentRating] = useState(null);
  const [ratingValue, setRatingValue] = useState(4);
  const [feedback, setFeedback] = useState("");
  const [latestResult, setLatestResult] = useState(null);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [savingRating, setSavingRating] = useState(false);
  const [hasSummarizedOnce, setHasSummarizedOnce] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session?.token) {
      return;
    }
    loadConversations(session.token);
  }, [session]);

  useEffect(() => {
    if (!session?.token || !selectedConversationId) {
      setConversationLoading(false);
      setMessages([]);
      setCurrentRating(null);
      setLatestResult(null);
      setFeedback("");
      return;
    }
    setMessages([]);
    setCurrentRating(null);
    setLatestResult(null);
    setFeedback("");
    hydrateConversation(session.token, selectedConversationId);
  }, [selectedConversationId, session]);

  useEffect(() => {
    const savedFormat = localStorage.getItem("summvi_output_format");
    const savedLength = localStorage.getItem("summvi_summary_length");
    if (savedFormat) setOutputFormat(savedFormat);
    if (savedLength) setSummaryLength(savedLength);
  }, []);

  useEffect(() => {
    localStorage.setItem("summvi_output_format", outputFormat);
    if (!booting && text.trim() && hasSummarizedOnce) {
      handleSummarize();
    }
  }, [outputFormat]);

  useEffect(() => {
    localStorage.setItem("summvi_summary_length", summaryLength);
    if (!booting && text.trim() && hasSummarizedOnce) {
      handleSummarize();
    }
  }, [summaryLength]);

  useEffect(() => {
    if (!toast) {
      return undefined;
    }
    const timer = window.setTimeout(() => setToast(""), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  function renderFormattedContent(content, limit = 0) {
    if (!content) return null;
    if (outputFormat === "paragraph") {
      const sanitized = (content || "").replace(/^[\s-•*]+/gm, "").trim();
      return <p className="summary-paragraph">{sanitized}</p>;
    }
    let bullets = splitSummary(content);
    if (limit > 0) {
      bullets = bullets.slice(0, limit);
    }
    return (
      <ul className="summary-bullets">
        {bullets.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    );
  }

  function renderHistoryView() {
    return (
      <div className="history-view-container">
        <div className="view-header">
          <h2>Lịch sử tóm tắt</h2>
          <p>Xem lại các bản tóm tắt đã thực hiện trong quá khứ.</p>
        </div>

        {loadingHistory ? (
          <div className="loading-state">Đang tải lịch sử...</div>
        ) : conversations.length === 0 ? (
          <div className="empty-state">
            <p>Chưa có cuộc hội thoại nào.</p>
            <button className="primary-btn" onClick={() => setActiveView("composer")}>
              Thực hiện bản tóm tắt đầu tiên
            </button>
          </div>
        ) : (
          <div className="history-grid">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className="conversation-card"
                onClick={() => {
                  setSelectedConversationId(conversation.id);
                  setActiveView("detail");
                }}
              >
                <div className="card-header">
                  <h4 className="card-title">{conversation.title || "Tóm tắt văn bản"}</h4>
                  <span className="card-date">{formatDate(conversation.created_at)}</span>
                </div>
                <p className="card-preview">
                  Bấm để xem chi tiết nội dung và các thông số phân tích.
                </p>
                <div className="card-footer">
                  <span className="metric-badge">ID: {conversation.id.slice(0, 8)}</span>
                  <button
                    className="card-delete-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteConversation(conversation.id);
                    }}
                  >
                    Xóa
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  function renderDetailView() {
    const exchangePairs = [];
    for (let i = 0; i < messages.length; i++) {
      if (messages[i].is_user) {
        const assistantMsg = messages.find(
          (m, idx) => idx > i && !m.is_user && m.conversation_id === messages[i].conversation_id
        );
        exchangePairs.push({
          user: messages[i],
          assistant: assistantMsg,
        });
      }
    }

    return (
      <div className="history-view-container">
        <div className="detail-view-header">
          <button className="back-btn" onClick={() => setActiveView("history")}>
            ← Quay lại
          </button>
          <h2>{selectedConversation?.title || "Chi tiết tóm tắt"}</h2>
        </div>

        {conversationLoading ? (
          <div className="loading-state">Đang tải chi tiết...</div>
        ) : (
          <div className="exchange-list">
            {exchangePairs.length === 0 && <p>Không tìm thấy nội dung trao đổi.</p>}
            {exchangePairs.map((pair, index) => (
              <div key={index} className="exchange-box">
                <div className="exchange-prompt">
                  <label>Nội dung gốc</label>
                  <p>{pair.user.content}</p>
                </div>
                <div className="exchange-result">
                  <label>Bản tóm tắt thông minh</label>
                  {pair.assistant ? (
                    <>
                      {renderFormattedContent(pair.assistant.content)}
                      <div className="exchange-metrics">
                        <div className="mini-chip">
                          Số chữ: <strong>{countWords(pair.assistant.content)}</strong>
                        </div>
                        <div className="mini-chip">
                          Thời gian: <strong>{formatDate(pair.assistant.created_at)}</strong>
                        </div>
                      </div>
                    </>
                  ) : (
                    <p className="text-muted italic">Đang chờ phản hồi hoặc không có dữ liệu...</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  const selectedConversation = useMemo(
    () => conversations.find((item) => item.id === selectedConversationId) || null,
    [conversations, selectedConversationId],
  );

  const composerWordCount = useMemo(() => countWords(text), [text]);

  const summaryBullets = useMemo(
    () => splitSummary(latestResult?.summary || latestResult?.content || ""),
    [latestResult],
  );
  const isAdminUser = session?.role === "admin";
  const hasResultPanel = submitting || conversationLoading || Boolean(latestResult) || messages.length > 0;
  const summaryText = latestResult?.summary || latestResult?.content || "";
  const summaryWordCount = latestResult?.metrics?.summary_word_count ?? countWords(summaryText);
  const inputWordCount =
    latestResult?.metrics?.input_word_count ?? countWords(messages.find((message) => message.is_user)?.content || text);
  const compressionRatio =
    latestResult?.metrics?.compression_ratio ??
    (inputWordCount > 0 ? 1 - summaryWordCount / inputWordCount : 0);
  const lengthRatio =
    latestResult?.metrics?.length_ratio ??
    (inputWordCount > 0 ? summaryWordCount / inputWordCount : 0);

  function invalidateConversationHydration() {
    hydrateRequestIdRef.current += 1;
  }

  function resetConversationView() {
    invalidateConversationHydration();
    setSelectedConversationId("");
    setMessages([]);
    setCurrentRating(null);
    setLatestResult(null);
    setFeedback("");
    setRatingValue(4);
    setConversationLoading(false);
    setHasSummarizedOnce(false);
  }

  async function loadConversations(token, preferredConversationId = "") {
    setLoadingHistory(true);
    try {
      const items = await listConversations(token);
      setConversations(items);

      const nextConversationId =
        preferredConversationId || selectedConversationId || items[0]?.id || "";
      setSelectedConversationId(nextConversationId);
    } catch (requestError) {
      setError(requestError.message || "Không thể tải lịch sử hội thoại.");
    } finally {
      setLoadingHistory(false);
    }
  }

  async function hydrateConversation(token, conversationId) {
    /**
     * Load chi tiết conversation từ API và populate vào UI state.
     *
     * Race condition handling:
     * - Dùng requestId để track request mới nhất
     * - Nếu có request mới được gọi trước khi request cũ hoàn thành, ignore kết quả của request cũ
     * - Pattern này tránh state bị overwrite bởi response chậm hơn
     */
    const requestId = ++hydrateRequestIdRef.current;
    setConversationLoading(true);
    try {
      const [messageRows, rating] = await Promise.all([
        getConversationMessages(token, conversationId),
        getConversationRating(token, conversationId).catch(() => null),
      ]);
      // Check nếu có request mới hơn đã được gọi -> ignore response này
      if (requestId !== hydrateRequestIdRef.current) {
        return;
      }
      setMessages(messageRows);
      setCurrentRating(rating);
      setRatingValue(rating?.rating || 4);
      setFeedback(rating?.feedback || "");

      const assistantMessage = [...messageRows].reverse().find((item) => !item.is_user);
      if (assistantMessage) {
        setHasSummarizedOnce(true);
        setLatestResult((current) => ({
          ...current,
          summary: assistantMessage.content,
          content: assistantMessage.content,
          conversation_id: conversationId,
          created_at: assistantMessage.created_at,
          metrics: current?.metrics || {},
        }));
      }
    } catch (requestError) {
      setError(requestError.message || "Không thể tải nội dung hội thoại.");
    } finally {
      if (requestId === hydrateRequestIdRef.current) {
        setConversationLoading(false);
      }
    }
  }

  async function handleFileUpload(file) {
    if (!session?.token) {
      setError("Cần đăng nhập để sử dụng tính năng tải tài liệu.");
      return;
    }
    const validTypes = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"];
    if (!validTypes.includes(file.type) && !file.name.endsWith(".txt")) {
      setError("Định dạng file không hợp lệ. Vui lòng chọn .pdf, .docx hoặc .txt");
      return;
    }

    setError("");
    setIsExtracting(true);
    setIsDragging(false);
    try {
      const result = await uploadDocument(session.token, file);
      setText(result.content);
      setActiveTab("text");
      setToast(`Đã trích xuất ${result.word_count} từ từ file ${result.filename}`);
    } catch (requestError) {
      setError(requestError.message || "Không thể trích xuất văn bản từ file.");
    } finally {
      setIsExtracting(false);
    }
  }

  async function handleSummarize() {
    /**
     * Gọi API tạo tóm tắt với fallback logic.
     *
     * Flow:
     * 1. Nếu có session token: gọi authenticated endpoint
     * 2. Nếu 401 (token expired): fallback về legacy endpoint (không cần auth)
     * 3. Nếu không có token: dùng legacy endpoint ngay
     * 4. Sau khi tạo xong: reload conversation list để sync UI
     */
    const inputText = text;
    if (!inputText.trim()) {
      setError("Cần nhập hoặc tải lên nội dung văn bản để tóm tắt.");
      return;
    }

    if (!selectedConversationId) {
      resetConversationView();
    }
    setSubmitting(true);
    setError("");

    try {
      const requestPayload = {
        text: inputText,
        summary_length: summaryLength,
        output_format: outputFormat,
        conversation_title: conversationTitle || undefined,
        conversation_id: selectedConversationId || undefined,
      };

      let response;
      if (session?.token) {
        try {
          response = await summarizeText(session.token, requestPayload);
        } catch (requestError) {
          // Fallback: nếu token expired, thử legacy endpoint
          if (requestError?.status === 401) {
            response = await summarizeLegacy(requestPayload);
          } else {
            throw requestError;
          }
        }
      } else {
        response = await summarizeLegacy(requestPayload);
      }

      if (session?.token && response?.conversation_id) {
        await loadConversations(session.token, response.conversation_id);
      }

      setToast("Đã tạo bản tóm tắt mới.");
      setLatestResult(response);
      setHasSummarizedOnce(true);
    } catch (requestError) {
      setError(requestError.message || "Không thể tạo bản tóm tắt.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteConversation(convId = selectedConversationId) {
    if (!session?.token || !convId) {
      return;
    }

    try {
      await deleteConversation(session.token, convId);
      const remainingItems = conversations.filter((item) => item.id !== convId);
      setConversations(remainingItems);

      if (convId === selectedConversationId) {
        setSelectedConversationId("");
        setMessages([]);
        setCurrentRating(null);
        setLatestResult(null);
        if (activeView === "detail") setActiveView("history");
      }
      setToast("Đã xóa hội thoại.");
    } catch (requestError) {
      setError(requestError.message || "Không thể xóa hội thoại.");
    }
  }

  async function handleSaveRating(nextValue = ratingValue) {
    if (!session?.token || !selectedConversationId) {
      return;
    }

    setSavingRating(true);
    setError("");

    try {
      const rating = await upsertRating(session.token, {
        conversation_id: selectedConversationId,
        rating: Number(nextValue),
        feedback,
      });
      setCurrentRating(rating);
      setRatingValue(rating.rating);
      setToast("Đã lưu đánh giá.");
    } catch (requestError) {
      setError(requestError.message || "Không thể lưu đánh giá.");
    } finally {
      setSavingRating(false);
    }
  }

  async function handleStarClick(value) {
    setRatingValue(value);
    await handleSaveRating(value);
  }

  async function handleCopySummary() {
    const summary = latestResult?.summary || latestResult?.content;
    if (!summary) {
      return;
    }

    try {
      await navigator.clipboard.writeText(summary);
      setToast("Đã sao chép vào clipboard.");
    } catch (_error) {
      setToast("Không thể sao chép trên trình duyệt hiện tại.");
    }
  }

  function handleResetComposer() {
    resetConversationView();
    setText("");
    setConversationTitle("");
    setError("");
  }

  function handleLogout() {
    clearStoredSession();
    setSession(null);
    setConversations([]);
    resetConversationView();
    router.replace("/login");
    router.refresh();
  }

  if (booting) {
    return <main className="app-loading">Đang tải workspace...</main>;
  }

  if (!session?.token) {
    return (
      <main className="auth-redirect-shell">
        <section className="auth-redirect-card">
          <div className="logo-area">
            <div className="logo-icon">SV</div>
            <h2>SummVi</h2>
          </div>
          <h1>Cần đăng nhập để truy cập giao diện workspace.</h1>
          <p>
            Trang này được thiết kế theo mẫu frontend trong project zip và nối trực tiếp đến các
            endpoint có xác thực của backend.
          </p>
          <div className="hero-links">
            <Link href="/login">Đăng nhập</Link>
            <Link href="/register">Đăng ký</Link>
          </div>
        </section>
      </main>
    );
  }

  return (
    <>
      <div className={`app-container ${isSidebarOpen ? "sidebar-open" : ""}`}>
        <div
          className="sidebar-backdrop"
          onClick={() => setIsSidebarOpen(false)}
        />
        <aside className="sidebar">
          <div
            className="logo-area"
            onClick={() => {
              setActiveView("composer");
              handleResetComposer();
            }}
            style={{ cursor: "pointer" }}
          >
            <div className="logo-icon">SV</div>
            <h2>SummVi</h2>
          </div>

          <button
            className={`new-chat-btn ${activeView === "composer" ? "active" : ""}`}
            onClick={() => {
              handleResetComposer();
              setActiveView("composer");
            }}
            type="button"
          >
            + Tạo tóm tắt mới
          </button>

          <div className="settings-nav">
            <p className="section-title">Điều hướng</p>
            <ul className="history-list">
              <li
                className={`history-item ${activeView === "composer" ? "active" : ""}`}
                onClick={() => setActiveView("composer")}
              >
                <span>Trang chủ</span>
              </li>
              <li
                className={`history-item ${activeView === "history" ? "active" : ""}`}
                onClick={() => setActiveView("history")}
              >
                <span>Lịch sử tóm tắt</span>
              </li>
            </ul>
          </div>

        </aside>

        <main className="main-content">
          <header className="topbar">
            <button
              className="hamburger-btn"
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              type="button"
            >
              ☰
            </button>
            <div className="breadcrumb">
              <span>{selectedConversation?.title || "Tóm tắt mới"}</span>
            </div>
            <div className="topbar-actions">
              <div className="topbar-user">
                <div className="avatar topbar-avatar">{getInitials(session.email)}</div>
                <div className="topbar-user-info">
                  <p className="topbar-user-name">{session.email}</p>
                  <p className="topbar-user-role">
                    {isAdminUser ? "Quản trị viên" : "Người dùng tiêu chuẩn"}
                  </p>
                </div>
              </div>
              <Link className="icon-btn" href="/settings" title="Cài đặt">
                ⚙
              </Link>
              {isAdminUser ? (
                <Link className="icon-btn" href="/admin" title="Quản trị">
                  AD
                </Link>
              ) : null}
              <button className="icon-btn" onClick={handleLogout} type="button" title="Đăng xuất">
                ⎋
              </button>
            </div>
          </header>

          <div className="workspace">
            {activeView === "composer" ? (
              <>
                <div className="workspace-header">
                  <h1>
                    Sức mạnh AI, <span className="text-gradient">tóm gọn</span> mọi văn bản.
                  </h1>
                  <p>
                    Nhập văn bản, đường dẫn hoặc mở bảng tài liệu để thực hiện tóm tắt. Hệ thống đang
                    sẵn sàng xử lý và cung cấp thông tin hữu ích cho bạn.
                  </p>
                </div>

                <div className="summary-preview-card">
                  <div className="result-header">
                    <h3>Kết quả tóm tắt</h3>
                    <button
                      className="copy-btn"
                      onClick={() =>
                        document.getElementById("resultArea")?.scrollIntoView({ behavior: "smooth" })
                      }
                      type="button"
                    >
                      Xem chi tiết
                    </button>
                  </div>

                  {hasResultPanel ? (
                    submitting || conversationLoading ? (
                      <div className="loading-state compact-loading" id="loadingState">
                        <div className="spinner-container">
                          <div className="spinner" />
                        </div>
                        <p>
                          {submitting
                            ? "AI đang xử lý bản tóm tắt..."
                            : "Đang tải nội dung hội thoại..."}
                        </p>
                      </div>
                    ) : (
                      <div className="final-output compact-output" id="finalOutputPreview">
                        {renderFormattedContent(
                          latestResult?.summary ||
                          latestResult?.content ||
                          [...messages].reverse().find((m) => !m.is_user)?.content,
                          5
                        )}

                        <div className="metrics-strip compact-metrics">
                          <div className="metric-chip">
                            <span>Tỷ lệ chiều dài</span>
                            <strong>{lengthRatio.toFixed(3)}</strong>
                          </div>
                          <div className="metric-chip">
                            <span>Tỷ lệ nén</span>
                            <strong>{compressionRatio.toFixed(3)}</strong>
                          </div>
                          <div className="metric-chip">
                            <span>Số chữ summary</span>
                            <strong>{summaryWordCount}</strong>
                          </div>
                        </div>
                      </div>
                    )
                  ) : (
                    <div className="empty-preview">
                      <p>Nhập văn bản bên dưới để bắt đầu tóm tắt bằng AI.</p>
                    </div>
                  )}
                </div>

                <div className="composer-card">
                  <div className="tabs">
                    <button
                      className={`tab-btn ${activeTab === "text" ? "active" : ""}`}
                      onClick={() => setActiveTab("text")}
                      type="button"
                    >
                      Văn bản
                    </button>
                    <button
                      className={`tab-btn ${activeTab === "file" ? "active" : ""}`}
                      onClick={() => setActiveTab("file")}
                      type="button"
                    >
                      Tải tài liệu
                    </button>
                  </div>

                  <div className="tab-content">
                    {activeTab === "text" ? (
                      <div className="input-panel active">
                        <input
                          className="title-input"
                          onChange={(event) => setConversationTitle(event.target.value)}
                          placeholder="Tiêu đề hội thoại (tùy chọn)"
                          type="text"
                          value={conversationTitle}
                        />
                        <textarea
                          className="main-textarea"
                          onChange={(event) => setText(event.target.value)}
                          placeholder={QUICK_START_TEXT}
                          value={text}
                        />
                        <div className="textarea-footer">
                          <span className={composerWordCount > 5000 ? "text-error" : ""}>
                            {composerWordCount} / 5000 từ
                          </span>
                          <button className="clear-btn" onClick={() => setText("")} type="button">
                            Xóa tất cả
                          </button>
                        </div>
                      </div>
                    ) : null}

                    {activeTab === "file" ? (
                      <div className="input-panel active">
                        <input
                          type="file"
                          accept=".pdf,.docx,.txt"
                          style={{ display: "none" }}
                          id="file-upload-input"
                          onChange={(e) => {
                            if (e.target.files?.[0]) {
                              handleFileUpload(e.target.files[0]);
                            }
                          }}
                        />
                        <div
                          className={`upload-zone ${isExtracting ? "loading" : ""} ${isDragging ? "dragging" : ""}`}
                          onClick={() => document.getElementById("file-upload-input")?.click()}
                          onDragOver={(e) => {
                            e.preventDefault();
                            setIsDragging(true);
                          }}
                          onDragLeave={() => setIsDragging(false)}
                          onDrop={(e) => {
                            e.preventDefault();
                            setIsDragging(false);
                            if (e.dataTransfer.files?.[0]) {
                              handleFileUpload(e.dataTransfer.files[0]);
                            }
                          }}
                        >
                          <div className="upload-icon-wrapper">
                            <svg className="upload-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                              <path d="M7 10L12 5L17 10M12 5V19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          </div>
                          <p className="upload-main-text">
                            {isExtracting ? "Đang trích xuất văn bản..." : "Kéo thả file vào đây hoặc click để chọn file"}
                          </p>
                          <span className="upload-sub-text">Hỗ trợ .pdf, .docx, .txt (tối đa 20MB)</span>
                          {isExtracting && <div className="loading-bar-container"><div className="loading-bar-fill"></div></div>}
                        </div>
                        <div className="placeholder-info">
                          <p>
                            Sau khi tải lên, nội dung sẽ được trích xuất vào tab "Văn bản" để bạn có thể xem lại và chỉnh sửa.
                          </p>
                          <p className="panel-note">
                            Giới hạn trích xuất tối đa 5000 từ để đảm bảo chất lượng tóm tắt tốt nhất.
                          </p>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>

                <div className="action-bar">
                  <div className="settings-group">
                    <div className="setting-item">
                      <label>Độ dài tóm tắt</label>
                      <div className="segmented-control">
                        {LENGTH_OPTIONS.map((option) => (
                          <button
                            key={option.value}
                            className={`segment ${summaryLength === option.value ? "active" : ""}`}
                            onClick={() => setSummaryLength(option.value)}
                            type="button"
                          >
                            {option.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="setting-item">
                      <label>Kiểu trình bày</label>
                      <div className="select-box">
                        <select
                          onChange={(event) => setOutputFormat(event.target.value)}
                          value={outputFormat}
                        >
                          <option value="bullet">Gạch đầu dòng</option>
                          <option value="paragraph">Đoạn văn tự nhiên</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="main-actions">
                    {error ? <span className="error-message">{error}</span> : null}
                    <button
                      className="primary-btn pulse"
                      disabled={submitting}
                      onClick={handleSummarize}
                      type="button"
                    >
                      {submitting ? "Đang xử lý..." : "Tạo tóm tắt"}
                    </button>
                  </div>
                </div>

                {(submitting || conversationLoading || latestResult || messages.length > 0) && (
                  <div className="result-area" id="resultArea">
                    <div className="result-header">
                      <h3>Kết quả tóm tắt</h3>
                      <div className="result-actions">
                        <div className="star-rating">
                          {STAR_VALUES.map((val) => (
                            <button
                              key={val}
                              className={`star ${ratingValue >= val ? "active" : ""}`}
                              onClick={() => handleStarClick(val)}
                              type="button"
                            >
                              ★
                            </button>
                          ))}
                        </div>
                        <button className="copy-btn" onClick={handleCopySummary} type="button">
                          Sao chép
                        </button>
                      </div>
                    </div>

                    {submitting || conversationLoading ? (
                      <div className="loading-state" id="loadingState">
                        <div className="spinner-container">
                          <div className="spinner" />
                        </div>
                        <div className="loading-text">
                          <div className="skeleton line long" />
                          <div className="skeleton line medium" />
                        </div>
                      </div>
                    ) : (
                      <div className="final-output" id="finalOutput">
                        {!(latestResult || messages.length > 0) ? (
                          <p className="empty-output">Chưa có kết quả tóm tắt.</p>
                        ) : (
                          renderFormattedContent(
                            latestResult?.summary ||
                            latestResult?.content ||
                            [...messages].reverse().find((m) => !m.is_user)?.content
                          )
                        )}

                        <div className="metrics-strip">
                          <div className="metric-chip">
                            <span>Tỷ lệ chiều dài</span>
                            <strong>{lengthRatio.toFixed(3)}</strong>
                          </div>
                          <div className="metric-chip">
                            <span>Tỷ lệ nén</span>
                            <strong>{compressionRatio.toFixed(3)}</strong>
                          </div>
                          <div className="metric-chip">
                            <span>Số chữ summary</span>
                            <strong>{summaryWordCount}</strong>
                          </div>
                          <div className="metric-chip">
                            <span>Số chữ đầu vào</span>
                            <strong>{inputWordCount}</strong>
                          </div>
                          <div className="metric-chip">
                            <span>Thời gian tạo</span>
                            <strong>{formatDate(latestResult?.created_at)}</strong>
                          </div>
                        </div>

                        <div className="result-subgrid">
                          <div className="transcript-card">
                            <div className="mini-header">
                              <h4>Transcript hội thoại</h4>
                              {selectedConversationId ? (
                                <button
                                  className="clear-btn"
                                  onClick={() => handleDeleteConversation()}
                                  type="button"
                                >
                                  Xóa hội thoại
                                </button>
                              ) : null}
                            </div>
                            <div className="message-list">
                              {messages.length === 0 ? <p>Chưa có tin nhắn nào.</p> : null}
                              {messages.map((message) => (
                                <div
                                  key={message.id}
                                  className={`message-bubble ${message.is_user ? "user" : "assistant"
                                    }`}
                                >
                                  <div className="message-row">
                                    <strong>{message.is_user ? "Người dùng" : "SummVi"}</strong>
                                    <span>{formatDate(message.created_at)}</span>
                                  </div>
                                  {message.is_user ? (
                                    <p>{message.content}</p>
                                  ) : (
                                    renderFormattedContent(message.content)
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="feedback-card">
                            <div className="mini-header">
                              <h4>Phản hồi</h4>
                            </div>
                            <textarea
                              className="feedback-textarea"
                              onChange={(event) => setFeedback(event.target.value)}
                              placeholder="Mô tả vấn đề về model, tốc độ, chất lượng summary..."
                              value={feedback}
                            />
                            <button
                              className="copy-btn save-rating-btn"
                              disabled={!selectedConversationId || savingRating}
                              onClick={() => handleSaveRating(ratingValue)}
                              type="button"
                            >
                              {savingRating ? "Đang lưu..." : "Lưu đánh giá"}
                            </button>
                            <p className="rating-note">
                              {currentRating
                                ? `Đánh giá hiện tại: ${currentRating.rating}/5`
                                : "Chưa có đánh giá cho hội thoại này."}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : activeView === "history" ? (
              renderHistoryView()
            ) : (
              renderDetailView()
            )}
          </div>
        </main>
      </div>

      <div className={`toast-notification ${toast ? "show" : ""}`}>{toast || "..."}</div>
    </>
  );
}
