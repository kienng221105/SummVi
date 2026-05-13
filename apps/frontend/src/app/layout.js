import "./globals.css";

export const metadata = {
  title: "SummVi",
  description: "Nền tảng tóm tắt báo tiếng Việt."
};

export default function RootLayout({ children }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
