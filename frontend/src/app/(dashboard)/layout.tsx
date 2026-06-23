import Sidebar from "@/components/layout/Sidebar";

/**
 * Dashboard layout with persistent sidebar.
 * All pages under (dashboard) route group share this layout.
 */
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[260px] p-8">
        {children}
      </main>
    </div>
  );
}
