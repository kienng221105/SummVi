import AuthPage from "../components/auth-page";


export const metadata = {
  title: "Đăng ký | SummVi",
};


export default function RegisterPage() {
  return (
    <AuthPage
      mode="register"
      title="Tạo tài khoản mới"
      subtitle="Đăng ký để trải nghiệm dịch vụ tóm tắt báo tiếng Việt"
    />
  );
}
