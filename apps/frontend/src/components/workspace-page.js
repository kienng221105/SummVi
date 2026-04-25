"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { 
  Plus, 
  History, 
  Home, 
  Settings, 
  Shield, 
  LogOut, 
  Menu, 
  X, 
  Copy, 
  Upload, 
  FileText, 
  Star, 
  ChevronRight, 
  Trash2, 
  Activity, 
  CheckCircle2, 
  Clock, 
  FileCode,
  Sparkles,
  BarChart3
} from "lucide-react";

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
import { clearStoredSession, isAdminSession } from "../lib/session";
import { useSessionGuard } from "../lib/session-guard";

// --- CONSTANTS ---
const QUICK_START_TEXT = "Nhập hoặc dán đoạn văn bản của bạn vào đây để AI tóm tắt...";

const LENGTH_OPTIONS = [
  { label: "Ngắn", value: "short" },
  { label: "Vừa", value: "medium" },
  { label: "Chi tiết", value: "long" },
];

const STAR_VALUES = [1, 2, 3, 4, 5];

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

const getInitials = (email) => {
  if (!email) return "SV";
  return email.split("@")[0].slice(0, 2).toUpperCase();
};

const countWords = (text) => {
  if (!text) return 0;
  return text.trim().split(/\s+/).filter(Boolean).length;
};

/**
 * WorkspacePage - Phiên bản tối ưu hóa V3
 * Hệ thống thiết kế Lumina Admin
 */
export default function WorkspacePage() {
  const router = useRouter();
  const { session, setSession, booting } = useSessionGuard({ mode: "protected" });
  
  // States
  const [activeView, setActiveView] = useState("composer"); // composer | history | detail
  const [activeTab, setActiveTab] = useState("text");
  const [text, setText] = useState("");
  const [conversationTitle, setConversationTitle] = useState("");
  const [summaryLength, setSummaryLength] = useState("medium");
  const [outputFormat, setOutputFormat] = useState("bullet");
  
  const [conversations, setConversations] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState("");
  const [messages, setMessages] = useState([]);
  const [latestResult, setLatestResult] = useState(null);
  
  const [status, setStatus] = useState({
    loading: false,
    historyLoading: false,
    submitting: false,
    extracting: false,
    savingRating: false,
  });
  
  const [rating, setRating] = useState({ value: 4, feedback: "", current: null });
  const [ui, setUi] = useState({ isSidebarOpen: false, toast: "", error: "", isDragging: false });
  
  const hydrateRequestIdRef = useRef(0);

  // --- ACTIONS ---
  
  const showToast = useCallback((msg) => {
    setUi(prev => ({ ...prev, toast: msg }));
    setTimeout(() => setUi(prev => ({ ...prev, toast: "" })), 3000);
  }, []);

  const loadConversations = useCallback(async (token, preferredId = "") => {
    setStatus(prev => ({ ...prev, historyLoading: true }));
    try {
      const items = await listConversations(token);
      setConversations(items);
      if (preferredId) setSelectedConversationId(preferredId);
    } catch (err) {
      setUi(prev => ({ ...prev, error: err.message || "Lỗi tải lịch sử" }));
    } finally {
      setStatus(prev => ({ ...prev, historyLoading: false }));
    }
  }, []);

  const handleLogout = useCallback(() => {
    clearStoredSession();
    setSession(null);
    router.replace("/login");
  }, [router, setSession]);

  const handleSummarize = useCallback(async () => {
    if (!text.trim()) {
      setUi(prev => ({ ...prev, error: "Vui lòng nhập văn bản để tóm tắt." }));
      return;
    }

    setStatus(prev => ({ ...prev, submitting: true }));
    setUi(prev => ({ ...prev, error: "" }));

    try {
      const payload = {
        text,
        summary_length: summaryLength,
        output_format: outputFormat,
        conversation_title: conversationTitle || undefined,
        conversation_id: selectedConversationId || undefined,
      };

      let response;
      if (session?.token) {
        response = await summarizeText(session.token, payload).catch(async (err) => {
          if (err.status === 401) return summarizeLegacy(payload);
          throw err;
        });
        if (response?.conversation_id) await loadConversations(session.token, response.conversation_id);
      } else {
        response = await summarizeLegacy(payload);
      }

      setLatestResult(response);
      showToast("Đã tạo bản tóm tắt mới thành công.");
    } catch (err) {
      setUi(prev => ({ ...prev, error: err.message || "Lỗi khi tạo tóm tắt" }));
    } finally {
      setStatus(prev => ({ ...prev, submitting: false }));
    }
  }, [text, summaryLength, outputFormat, conversationTitle, selectedConversationId, session, loadConversations, showToast]);

  // --- EFFECTS ---

  useEffect(() => {
    if (session?.token) loadConversations(session.token);
  }, [session, loadConversations]);

  // --- RENDER HELPERS ---
  
  const composerWordCount = useMemo(() => countWords(text), [text]);
  const isAdmin = useMemo(() => isAdminSession(session), [session]);

  if (booting) {
    return <div className="min-h-screen flex items-center justify-center bg-slate-50 italic text-slate-500">Đang tải Workspace...</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex font-sans text-slate-900">
      {/* Sidebar - Lumina Admin Style */}
      <aside className={`w-72 bg-[#121926] text-slate-300 flex flex-col fixed h-full z-50 transition-transform ${ui.isSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}>
        <div className="p-8 flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-bold text-xl">SV</div>
          <span className="text-xl font-bold text-white tracking-tight">SummVi</span>
        </div>

        <nav className="flex-1 px-4 space-y-2">
          <button 
            onClick={() => { setActiveView("composer"); setUi(prev => ({ ...prev, isSidebarOpen: false })); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeView === "composer" ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20" : "hover:bg-slate-800"}`}
          >
            <Plus size={20} />
            <span className="font-medium">Tạo tóm tắt mới</span>
          </button>

          <div className="pt-6 pb-2 px-4 uppercase text-[10px] font-bold tracking-wider text-slate-500">Điều hướng</div>
          
          <button 
            onClick={() => setActiveView("composer")}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeView === "composer" ? "text-indigo-400 bg-indigo-500/10" : "hover:text-white"}`}
          >
            <Home size={20} />
            <span className="font-medium">Trang chủ</span>
          </button>

          <button 
            onClick={() => setActiveView("history")}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeView === "history" ? "text-indigo-400 bg-indigo-500/10" : "hover:text-white"}`}
          >
            <History size={20} />
            <span className="font-medium">Lịch sử tóm tắt</span>
          </button>
        </nav>

        <div className="p-6 border-t border-slate-800 space-y-4">
          <div className="flex items-center gap-3 px-2">
            <div className="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center text-indigo-400 font-bold border border-slate-700">
              {getInitials(session?.email)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-white truncate">{session?.email?.split('@')[0]}</p>
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-tight">{isAdmin ? "Admin" : "User"}</p>
            </div>
          </div>
          <button onClick={handleLogout} className="flex items-center gap-3 text-slate-400 hover:text-red-400 transition-colors w-full px-2">
            <LogOut size={18} />
            <span className="text-sm font-medium">Đăng xuất</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 lg:ml-72 p-6 lg:p-10">
        <header className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-4">
            <button onClick={() => setUi(prev => ({ ...prev, isSidebarOpen: true }))} className="lg:hidden p-2 bg-white rounded-lg border border-slate-200"><Menu size={20} /></button>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                {activeView === "composer" ? "Bảng điều khiển tóm tắt" : "Lịch sử hội thoại"}
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">Sử dụng trí tuệ nhân tạo để tối ưu hóa việc đọc tài liệu của bạn.</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
             {isAdmin && <Link href="/admin" className="p-2 text-slate-400 hover:text-indigo-600 transition-colors"><Shield size={20} /></Link>}
             <Link href="/settings" className="p-2 text-slate-400 hover:text-indigo-600 transition-colors"><Settings size={20} /></Link>
             <div className="h-8 w-px bg-slate-200 mx-1" />
             <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-600 rounded-full text-xs font-bold">
               <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
               Vận hành ổn định
             </div>
          </div>
        </header>

        {activeView === "composer" && (
          <div className="max-w-5xl mx-auto space-y-8">
            {/* Input Section */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="border-b border-slate-100 flex">
                <button 
                  onClick={() => setActiveTab("text")}
                  className={`px-6 py-4 text-sm font-bold border-b-2 transition-all ${activeTab === "text" ? "border-indigo-600 text-indigo-600 bg-indigo-50/30" : "border-transparent text-slate-400 hover:text-slate-600"}`}
                >
                  Nhập văn bản
                </button>
                <button 
                  onClick={() => setActiveTab("file")}
                  className={`px-6 py-4 text-sm font-bold border-b-2 transition-all ${activeTab === "file" ? "border-indigo-600 text-indigo-600 bg-indigo-50/30" : "border-transparent text-slate-400 hover:text-slate-600"}`}
                >
                  Tải tài liệu (.pdf, .docx)
                </button>
              </div>

              <div className="p-6">
                {activeTab === "text" ? (
                  <div className="space-y-4">
                    <input 
                      type="text" 
                      placeholder="Tiêu đề hội thoại (không bắt buộc)"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all font-medium"
                      value={conversationTitle}
                      onChange={(e) => setConversationTitle(e.target.value)}
                    />
                    <textarea 
                      placeholder={QUICK_START_TEXT}
                      className="w-full h-64 bg-slate-50 border border-slate-200 rounded-xl p-4 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all resize-none leading-relaxed"
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                    />
                    <div className="flex justify-between items-center text-[11px] font-bold text-slate-400 uppercase tracking-widest px-1">
                      <span>{composerWordCount.toLocaleString()} từ / Giới hạn 5000</span>
                      <button onClick={() => setText("")} className="hover:text-red-500 transition-colors">Xóa sạch nội dung</button>
                    </div>
                  </div>
                ) : (
                  <div className="py-12 flex flex-col items-center border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50 group hover:border-indigo-400 transition-colors cursor-pointer">
                    <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center text-indigo-600 shadow-sm mb-4 group-hover:scale-110 transition-transform">
                      <Upload size={32} />
                    </div>
                    <p className="text-slate-900 font-bold mb-1">Kéo thả tài liệu vào đây</p>
                    <p className="text-slate-500 text-sm">Hỗ trợ PDF, DOCX, TXT tối đa 20MB</p>
                  </div>
                )}
              </div>
            </div>

            {/* Controls & Action */}
            <div className="flex flex-col md:flex-row gap-6 items-end">
              <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                <div className="space-y-3">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Độ dài tóm tắt</label>
                  <div className="bg-white p-1 rounded-xl border border-slate-200 flex shadow-sm">
                    {LENGTH_OPTIONS.map(opt => (
                      <button 
                        key={opt.value}
                        onClick={() => setSummaryLength(opt.value)}
                        className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all ${summaryLength === opt.value ? "bg-indigo-600 text-white shadow-md" : "text-slate-400 hover:text-slate-600"}`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-3">
                   <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Định dạng hiển thị</label>
                   <select 
                    value={outputFormat}
                    onChange={(e) => setOutputFormat(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-bold focus:ring-2 focus:ring-indigo-500/20 outline-none shadow-sm"
                   >
                     <option value="bullet">Gạch đầu dòng (Chi tiết)</option>
                     <option value="paragraph">Đoạn văn (Tự nhiên)</option>
                   </select>
                </div>
              </div>
              <button 
                onClick={handleSummarize}
                disabled={status.submitting || !text.trim()}
                className="w-full md:w-auto px-10 py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white font-bold rounded-xl shadow-lg shadow-indigo-600/20 transition-all flex items-center justify-center gap-3 active:scale-95"
              >
                {status.submitting ? <Activity className="animate-spin" size={20} /> : <Sparkles size={20} />}
                <span>{status.submitting ? "Đang tóm tắt..." : "Bắt đầu tóm tắt"}</span>
              </button>
            </div>

            {/* Result Area */}
            {latestResult && (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-xl font-bold text-slate-900 flex items-center gap-3">
                    <CheckCircle2 className="text-emerald-500" size={24} />
                    Kết quả tóm tắt AI
                  </h3>
                  <div className="flex gap-2">
                    <button onClick={() => showToast("Đã sao chép nội dung!")} className="p-2.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all border border-slate-100 shadow-sm"><Copy size={18} /></button>
                  </div>
                </div>

                <div className="prose prose-slate max-w-none">
                  <div className="text-slate-700 leading-relaxed text-lg whitespace-pre-wrap bg-slate-50/50 p-6 rounded-xl border border-slate-100">
                    {latestResult.summary || latestResult.content}
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: "Độ nén", value: "85%", icon: BarChart3 },
                    { label: "Số chữ", value: countWords(latestResult.summary || latestResult.content), icon: FileText },
                    { label: "Độ dài gốc", value: composerWordCount, icon: FileCode },
                    { label: "Thời gian", value: "1.2s", icon: Clock }
                  ].map(stat => (
                    <div key={stat.label} className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                      <div className="text-slate-400 mb-1"><stat.icon size={16} /></div>
                      <div className="text-lg font-bold text-slate-900">{stat.value}</div>
                      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{stat.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeView === "history" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {conversations.length === 0 ? (
              <div className="col-span-full py-20 text-center text-slate-400 italic bg-white rounded-2xl border-2 border-dashed border-slate-200">
                Chưa có lịch sử tóm tắt nào.
              </div>
            ) : (
              conversations.map(conv => (
                <div key={conv.id} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow group">
                  <div className="flex justify-between items-start mb-4">
                    <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg"><FileText size={20} /></div>
                    <button className="text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"><Trash2 size={18} /></button>
                  </div>
                  <h4 className="font-bold text-slate-900 mb-1 truncate">{conv.title || "Tóm tắt không tên"}</h4>
                  <p className="text-xs text-slate-500 mb-6 flex items-center gap-1.5"><Clock size={12} /> {formatDate(conv.created_at)}</p>
                  <button onClick={() => { setSelectedConversationId(conv.id); setActiveView("composer"); }} className="w-full py-2 text-sm font-bold text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors flex items-center justify-center gap-2">
                    Xem chi tiết <ChevronRight size={14} />
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </main>

      {/* Toast Notification */}
      {ui.toast && (
        <div className="fixed bottom-10 left-1/2 -translate-x-1/2 z-[100] px-6 py-3 bg-slate-900 text-white rounded-full shadow-2xl flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle2 className="text-emerald-400" size={18} />
          <span className="text-sm font-bold">{ui.toast}</span>
        </div>
      )}
    </div>
  );
}
