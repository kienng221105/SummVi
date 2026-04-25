import AdminConsole from "../components/admin-console";

/**
 * AdminPage component - Phiên bản JavaScript (.js)
 * Entry point cho route /admin
 */
export const metadata = {
  title: "Bảng điều khiển Admin | SummVi",
  description: "Quản trị hệ thống SummVi.",
};

export default function AdminPage() {
  return (
    <main className="min-h-screen bg-slate-50">
      <AdminConsole />
    </main>
  );
}
