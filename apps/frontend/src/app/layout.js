import "./globals.css";
import { Inter } from "next/font/google";

/**
 * Cấu hình Font Inter - Font chữ tiêu chuẩn của hệ thống thiết kế Lumina Admin.
 * Phiên bản JavaScript (.js)
 */
const inter = Inter({ 
  subsets: ["latin", "vietnamese"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata = {
  title: {
    default: "SummVi | Nền tảng tóm tắt Tiếng Việt thông minh",
    template: "%s | SummVi"
  },
  description: "Giải pháp tóm tắt văn bản dựa trên AI với công nghệ RAG.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="vi" className={`${inter.variable} scroll-smooth`}>
      <body className="font-sans antialiased bg-slate-50 text-slate-900">
        {children}
      </body>
    </html>
  );
}
