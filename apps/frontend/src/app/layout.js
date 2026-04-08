import "./globals.css";

export const metadata = {
  title: "SummVi",
  description: "Nền tảng tóm tắt tiếng Việt với RAG, đánh giá và giám sát BI."
};

export default function RootLayout({ children }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
