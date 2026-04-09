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
  upsertRating,
} from "../lib/api";
import { clearStoredSession } from "../lib/session";
import { useSessionGuard } from "../lib/session-guard";

const QUICK_START_TEXT =
  "Nhập một đoạn văn tiếng Việt để hệ thống ViT5 + RAG phân tích, tạo tóm tắt và ghi nhận log vận hành.";

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
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function getInitials(email) {
  if (!email) {
    return "SV";
  }
  return email.slice(0, 2).toUpperCase();
}

function splitSummary(summary) {
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
  const [activeTab, setActiveTab] = useState("text");
  const [text, setText] = useState(QUICK_START_TEXT);
  const [urlText, setUrlText] = useState("");
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
  const [savingRating, setSavingRating] = useState(false);
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
    if (!toast) {
      return undefined;
    }
    const timer = window.setTimeout(() => setToast(""), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const selectedConversation = useMemo(
    () => conversations.find((item) => item.id === selectedConversationId) || null,
    [conversations, selectedConversationId],
  );

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
    const requestId = ++hydrateRequestIdRef.current;
    setConversationLoading(true);
    try {
      const [messageRows, rating] = await Promise.all([
        getConversationMessages(token, conversationId),
        getConversationRating(token, conversationId).catch(() => null),
      ]);
      if (requestId !== hydrateRequestIdRef.current) {
        return;
      }
      setMessages(messageRows);
      setCurrentRating(rating);
      setRatingValue(rating?.rating || 4);
      setFeedback(rating?.feedback || "");

      const assistantMessage = [...messageRows].reverse().find((item) => !item.is_user);
      if (assistantMessage) {
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
      setError(requestError.message || "KhÃ´ng thá»ƒ táº£i ná»™i dung há»™i thoáº¡i.");
    } finally {
      if (requestId === hydrateRequestIdRef.current) {
        setConversationLoading(false);
      }
    }
  }

  async function handleSummarize() {
    const inputText = activeTab === "text" ? text : urlText;
    if (!inputText.trim()) {
      setError("Cần nhập nội dung văn bản hoặc đường dẫn.");
      return;
    }

    resetConversationView();
    setSubmitting(true);
    setError("");

    try {
      const requestPayload = {
        text: inputText,
        summary_length: summaryLength,
        output_format: outputFormat,
        conversation_title: conversationTitle || undefined,
      };

      let response;
      if (session?.token) {
        try {
          response = await summarizeText(session.token, requestPayload);
        } catch (requestError) {
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
    } catch (requestError) {
      setError(requestError.message || "Không thể tạo bản tóm tắt.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteConversation() {
    if (!session?.token || !selectedConversationId) {
      return;
    }

    try {
      await deleteConversation(session.token, selectedConversationId);
      const remainingItems = conversations.filter((item) => item.id !== selectedConversationId);
      setConversations(remainingItems);
      const nextConversationId = remainingItems[0]?.id || "";
      setSelectedConversationId(nextConversationId);
      setToast("Đã xóa hội thoại.");
      if (!nextConversationId) {
        setMessages([]);
        setCurrentRating(null);
        setLatestResult(null);
      }
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
    setUrlText("");
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
      <div className="app-container">
        <aside className="sidebar">
          <div className="logo-area">
            <div className="logo-icon">SV</div>
            <h2>SummVi</h2>
          </div>

          <button className="new-chat-btn" onClick={handleResetComposer} type="button">
            + Tạo tóm tắt mới
          </button>

          <div className="nav-section">
            <p className="section-title">Gần đây</p>
            <ul className="history-list">
              {loadingHistory ? <li className="history-item">Đang tải hội thoại...</li> : null}
              {!loadingHistory && conversations.length === 0 ? (
                <li className="history-item">Chưa có hội thoại nào.</li>
              ) : null}
              {conversations.map((conversation) => (
                <li
                  key={conversation.id}
                  className={`history-item ${
                    selectedConversationId === conversation.id ? "active" : ""
                  }`}
                  onClick={() => setSelectedConversationId(conversation.id)}
                >
                  <span>{conversation.title || "Tóm tắt văn bản"}</span>
                </li>
              ))}
            </ul>
          </div>

        </aside>

        <main className="main-content">
          <header className="topbar">
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
            <div className="workspace-header">
              <h1>
                Sức mạnh AI, <span className="text-gradient">tóm gọn</span> mọi văn bản.
              </h1>
              <p>
                Nhập văn bản, đường dẫn hoặc mở panel tài liệu để thao tác theo giao diện mẫu. Sử
                dụng thực tế hiện tại đang nối đến FastAPI summarization workflow.
              </p>
            </div>

            <div className="summary-preview-card">
              <div className="result-header">
                <h3>Kết quả tóm tắt</h3>
                <button
                  className="copy-btn"
                  onClick={() => document.getElementById("resultArea")?.scrollIntoView({ behavior: "smooth" })}
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
                    <p>{submitting ? "AI đang xử lý bản tóm tắt..." : "Đang tải nội dung hội thoại..."}</p>
                  </div>
                ) : (
                  <div className="final-output compact-output" id="finalOutputPreview">
                    {summaryBullets.length > 0 ? (
                      <ul className="summary-bullets">
                        {summaryBullets.slice(0, 5).map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="empty-output">Chưa có kết quả tóm tắt.</p>
                    )}

                    <div className="metrics-strip compact-metrics">
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
                <div className="result-empty-state">
                  <h4>Kết quả sẽ hiện ở đây</h4>
                  <p>Nhấn “Tạo tóm tắt” để xem summary và chỉ số ngay trên đầu trang.</p>
                </div>
              )}
            </div>

            <div className="editor-card">
              <div className="editor-tabs">
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
                <button
                  className={`tab-btn ${activeTab === "url" ? "active" : ""}`}
                  onClick={() => setActiveTab("url")}
                  type="button"
                >
                  Đường dẫn URL
                </button>
              </div>

              <div className="editor-body">
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
                      onChange={(event) => setText(event.target.value)}
                      placeholder="Dán văn bản tiếng Việt dài của bạn vào đây..."
                      value={text}
                    />
                    <div className="textarea-footer">
                      <span className="word-count">{text.trim().split(/\s+/).filter(Boolean).length} từ</span>
                      <button className="clear-btn" onClick={() => setText("")} type="button">
                        Xóa tất cả
                      </button>
                    </div>
                  </div>
                ) : null}

                {activeTab === "file" ? (
                  <div className="input-panel active">
                    <div className="dropzone">
                      <div className="drop-icon">PDF</div>
                      <p className="drop-title">Panel tải file được giữ theo giao diện mẫu.</p>
                      <p className="drop-desc">
                        Hiện backend chưa mở endpoint upload tài liệu trên frontend này, nên tab này
                        chỉ để giữ UX giống project zip.
                      </p>
                    </div>
                  </div>
                ) : null}

                {activeTab === "url" ? (
                  <div className="input-panel active">
                    <div className="url-wrapper">
                      <span>URL</span>
                      <input
                        onChange={(event) => setUrlText(event.target.value)}
                        placeholder="Dán URL và hệ thống sẽ tóm tắt nội dung mô tả"
                        type="text"
                        value={urlText}
                      />
                    </div>
                    <p className="panel-note">
                      Frontend sẽ gửi nguyên chuỗi này vào endpoint summarize hiện tại.
                    </p>
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
                      <option value="keypoints">Ý chính</option>
                    </select>
                  </div>
                </div>
              </div>

              <button
                className="summarize-btn"
                disabled={submitting}
                id="generateBtn"
                onClick={handleSummarize}
                type="button"
              >
                <span className="btn-text">{submitting ? "Đang xử lý..." : "Tạo tóm tắt"}</span>
                <span>{submitting ? "..." : ">"}</span>
              </button>
            </div>

            {error ? <p className="inline-error">{error}</p> : null}

            {(submitting || conversationLoading || latestResult || messages.length > 0) && (
              <div className="result-area" id="resultArea">
                <div className="result-header">
                  <h3>Kết quả tóm tắt</h3>
                  <div className="result-actions">
                    <div className="star-rating" title="Đánh giá chất lượng">
                      {STAR_VALUES.map((value) => (
                        <button
                          key={value}
                          className={`star-icon ${ratingValue >= value ? "filled" : ""}`}
                          disabled={!selectedConversationId || savingRating}
                          onClick={() => handleStarClick(value)}
                          type="button"
                        >
                          *
                        </button>
                      ))}
                    </div>
                    <button className="icon-btn copy-btn" onClick={handleCopySummary} type="button">
                      Sao chép
                    </button>
                  </div>
                </div>

                {submitting || conversationLoading ? (
                  <div className="loading-state" id="loadingState">
                    <div className="spinner-container">
                      <div className="spinner" />
                    </div>
                    <p>{submitting ? "AI đang phân tích và trích xuất ý chính..." : "Đang tải nội dung hội thoại..."}</p>
                    <div className="skeleton-lines">
                      <div className="skeleton line" />
                      <div className="skeleton line x-long" />
                      <div className="skeleton line long" />
                      <div className="skeleton line medium" />
                    </div>
                  </div>
                ) : (
                  <div className="final-output" id="finalOutput">
                    {summaryBullets.length > 0 ? (
                      <ul className="summary-bullets">
                        {summaryBullets.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="empty-output">Chưa có kết quả tóm tắt.</p>
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
                            <button className="clear-btn" onClick={handleDeleteConversation} type="button">
                              Xóa hội thoại
                            </button>
                          ) : null}
                        </div>
                        <div className="message-list">
                          {messages.length === 0 ? <p>Chưa có tin nhắn nào.</p> : null}
                          {messages.map((message) => (
                            <div
                              key={message.id}
                              className={`message-bubble ${message.is_user ? "user" : "assistant"}`}
                            >
                              <div className="message-row">
                                <strong>{message.is_user ? "Người dùng" : "SummVi"}</strong>
                                <span>{formatDate(message.created_at)}</span>
                              </div>
                              <p>{message.content}</p>
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
          </div>
        </main>
      </div>

      <div className={`toast-notification ${toast ? "show" : ""}`}>{toast || "..."}</div>
    </>
  );
}

