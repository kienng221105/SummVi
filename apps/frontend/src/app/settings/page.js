import SettingsConsole from "../components/settings-console";

/**
 * SettingsPage component - Phiên bản JavaScript (.js)
 */
export const metadata = {
  title: "Hồ sơ cá nhân | SummVi",
};

export default function SettingsPage() {
  return (
    <main className="min-h-screen bg-slate-50">
      <SettingsConsole />
    </main>
  );
}
