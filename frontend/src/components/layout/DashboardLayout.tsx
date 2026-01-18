"use client";

import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopNavbar } from "./TopNavbar";
import { cn } from "@/lib/utils";
import { useLocalStorage } from "@/hooks/use-local-storage";

interface DashboardLayoutProps {
  children: React.ReactNode;
  notificationCount?: number;
}

export function DashboardLayout({ children, notificationCount = 0 }: DashboardLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useLocalStorage(
    "sidebar-collapsed",
    false
  );

  return (
    <div className="min-h-screen flex bg-background">
      {/* Desktop Sidebar */}
      <div className="hidden md:flex">
        <Sidebar
          collapsed={sidebarCollapsed}
          onCollapsedChange={setSidebarCollapsed}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navbar */}
        <TopNavbar notificationCount={notificationCount} />

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
