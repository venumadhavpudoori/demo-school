"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, School } from "lucide-react";
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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth, User } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { useState } from "react";

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
    href: "/students",
    icon: GraduationCap,
    roles: ["admin", "teacher", "super_admin"],
  },
  {
    title: "Teachers",
    href: "/teachers",
    icon: Users,
    roles: ["admin", "super_admin"],
  },
  {
    title: "Classes",
    href: "/classes",
    icon: BookOpen,
    roles: ["admin", "teacher", "super_admin"],
  },
  {
    title: "Attendance",
    href: "/attendance",
    icon: ClipboardList,
    roles: ["admin", "teacher", "student", "parent", "super_admin"],
  },
  {
    title: "Grades",
    href: "/grades",
    icon: FileText,
    roles: ["admin", "teacher", "student", "parent", "super_admin"],
  },
  {
    title: "Timetable",
    href: "/timetable",
    icon: Calendar,
    roles: ["admin", "teacher", "student", "parent", "super_admin"],
  },
  {
    title: "Fees",
    href: "/fees",
    icon: DollarSign,
    roles: ["admin", "student", "parent", "super_admin"],
  },
  {
    title: "Leave Requests",
    href: "/leave-requests",
    icon: Clock,
    roles: ["admin", "teacher", "student", "super_admin"],
  },
  {
    title: "Announcements",
    href: "/announcements",
    icon: Megaphone,
    roles: ["admin", "teacher", "student", "parent", "super_admin"],
  },
  {
    title: "Reports",
    href: "/reports",
    icon: FileText,
    roles: ["admin", "super_admin"],
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
    roles: ["admin", "super_admin"],
  },
];

export function MobileSidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);

  // Filter nav items based on user role
  const filteredNavItems = navItems.filter((item) => {
    if (!user) return false;
    return item.roles.includes(user.role);
  });

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
          <span className="sr-only">Toggle menu</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64 p-0">
        <SheetHeader className="h-14 px-4 border-b flex flex-row items-center">
          <School className="h-6 w-6 text-primary mr-2" />
          <SheetTitle>School ERP</SheetTitle>
        </SheetHeader>
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-2">
            {filteredNavItems.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
              const Icon = item.icon;

              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    )}
                  >
                    <Icon className="h-5 w-5 shrink-0" />
                    <span>{item.title}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </SheetContent>
    </Sheet>
  );
}
