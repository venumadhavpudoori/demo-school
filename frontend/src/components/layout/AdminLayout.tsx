"use client";

import { AdminSidebar } from "./AdminSidebar";
import { AdminTopNavbar } from "./AdminTopNavbar";
import { cn } from "@/lib/utils";
import { useLocalStorage } from "@/hooks/use-local-storage";

interface AdminLayoutProps {
  children: React.ReactNode;
  notificationCount?: number;
}

export function AdminLayout({ children, notificationCount = 0 }: AdminLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useLocalStorage(
    "admin-sidebar-collapsed",
    false
  );

  return (
    <div className="min-h-screen flex bg-background">
      {/* Desktop Sidebar */}
      <div className="hidden md:flex">
        <AdminSidebar
          collapsed={sidebarCollapsed}
          onCollapsedChange={setSidebarCollapsed}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navbar */}
        <AdminTopNavbar notificationCount={notificationCount} />

        {/* Page Content */}
        <main
          className={cn(
            "flex-1 overflow-auto p-4 sm:p-6",
            "transition-all duration-300"
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
