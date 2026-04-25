import AuthPage from "../components/auth-page";

/**
 * LoginPage component - Phiên bản JavaScript (.js)
 */
export const metadata = {
  title: "Đăng nhập | SummVi",
};

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-white">
      <AuthPage
        mode="login"
        title="Đăng nhập vào SummVi"
        subtitle="Truy cập không gian tóm tắt và quản trị."
      />
    </main>
  );
}
