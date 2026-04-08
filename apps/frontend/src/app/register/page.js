import AuthPage from "../components/auth-page";


export const metadata = {
  title: "Đăng ký | SummVi",
};


export default function RegisterPage() {
  return (
    <AuthPage
      mode="register"
      title="Tạo tài khoản mới"
      subtitle="Đăng ký để lưu lịch sử tóm tắt, đánh giá kết quả và sử dụng các tính năng quản trị."
    />
  );
}
