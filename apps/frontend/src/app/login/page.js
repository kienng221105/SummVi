import AuthPage from "../components/auth-page";


export const metadata = {
  title: "Đăng nhập | SummVi",
};


export default function LoginPage() {
  return (
    <AuthPage
      mode="login"
      title="Đăng nhập vào SummVi"
      subtitle="Truy cập không gian tóm tắt báo tiếng Việt"
    />
  );
}
