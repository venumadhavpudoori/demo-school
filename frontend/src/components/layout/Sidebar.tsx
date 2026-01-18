"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  Users,
  GraduationCap,
  BookOpen,
  Calendar,
  ClipboardList,
  DollarSign,
  Clock,
  Megaphone,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  School,
  Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth, User } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: Array<User["role"]>;
}

const navItems: NavItem[] = [
  {
    title: "Dashboard",
    href: "/dashboard",
    icon: Home,
    roles: ["admin", "teacher", "student", "parent", "super_admin"],
  },
  {
    title: "Students",
    href: "/dashboard/students",
    icon: GraduationCap,
    roles: ["admin", "teacher", "super_admin"],
  },
  {
    title: "Teachers",
    href: "/dashboard/teachers",
    icon: Users,
    roles: ["admin", "super_admin"],
  },
  {
    title: "Classes",
    href: "/dashboard/classes",
    icon: BookOpen,
    roles: ["admin", "teacher", "super_admin"],
  },
  {
    title: "Attendance",
    href: "/dashboard/attendance",
    icon: ClipboardList,
    roles: ["admin", "teacher", "student", "parent", "super_admin"],
  },
  {
    title: "Grades",
    href: "/dashboard/grades",
    icon: FileText,
    roles: ["admin", "teacher", "student", "parent", "super_admin"],
  },
  {
    title: "Timetable",
    href: "/dashboard/timetable",
    icon: Calendar,
    roles: ["admin", "teacher", "student", "parent", "super_admin"],
  },
  {
    title: "Fees",
    href: "/dashboard/fees",
    icon: DollarSign,
    roles: ["admin", "student", "parent", "super_admin"],
  },
  {
    title: "Leave Requests",
    href: "/dashboard/leave-requests",
    icon: Clock,
    roles: ["admin", "teacher", "student", "super_admin"],
  },
  {
    title: "Announcements",
    href: "/dashboard/announcements",
    icon: Megaphone,
    roles: ["admin", "teacher", "student", "parent", "super_admin"],
  },
  {
    title: "Reports",
    href: "/dashboard/reports",
    icon: FileText,
    roles: ["admin", "super_admin"],
  },
  {
    title: "Settings",
    href: "/dashboard/settings",
    icon: Settings,
    roles: ["admin", "super_admin"],
  },
];

interface SidebarProps {
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
}

export function Sidebar({ collapsed = false, onCollapsedChange }: SidebarProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(collapsed);

  const handleCollapse = () => {
    const newCollapsed = !isCollapsed;
    setIsCollapsed(newCollapsed);
    onCollapsedChange?.(newCollapsed);
  };

  // Filter nav items based on user role
  const filteredNavItems = navItems.filter((item) => {
    if (!user) return false;
    return item.roles.includes(user.role);
  });

  // Check if user is super_admin
  const isSuperAdmin = user?.role === "super_admin";

  return (
    <aside
      className={cn(
        "flex flex-col h-full bg-sidebar border-r transition-all duration-300",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo/Brand */}
      <div className="flex items-center h-14 px-4 border-b">
        <Link href="/dashboard" className="flex items-center gap-2">
          <School className="h-6 w-6 text-primary shrink-0" />
          {!isCollapsed && (
            <span className="font-semibold text-lg truncate">School ERP</span>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-2">
          {filteredNavItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    isCollapsed && "justify-center px-2"
                  )}
                  title={isCollapsed ? item.title : undefined}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {!isCollapsed && <span>{item.title}</span>}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Super Admin Link - Only visible to super_admin users */}
        {isSuperAdmin && (
          <>
            <div className="my-4 px-4">
              <div className="border-t" />
            </div>
            <ul className="space-y-1 px-2">
              <li>
                <Link
                  href="/admin"
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                    pathname.startsWith("/admin")
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    isCollapsed && "justify-center px-2"
                  )}
                  title={isCollapsed ? "Super Admin" : undefined}
                >
                  <Shield className="h-5 w-5 shrink-0" />
                  {!isCollapsed && <span>Super Admin</span>}
                </Link>
              </li>
            </ul>
          </>
        )}
      </nav>

      {/* Collapse Toggle */}
      <div className="p-2 border-t">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCollapse}
          className={cn("w-full", isCollapsed ? "justify-center" : "justify-start")}
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" />
              <span className="ml-2">Collapse</span>
            </>
          )}
        </Button>
      </div>
    </aside>
  );
}
