"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  GraduationCap,
  Users,
  DollarSign,
  BookOpen,
  ClipboardList,
  Calendar,
  Megaphone,
  FileText,
  Plus,
  ArrowRight,
  Clock,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth, User } from "@/context/AuthContext";
import { api, ApiError } from "@/lib/api";

// Types for dashboard data
interface DashboardStats {
  totalStudents: number;
  totalTeachers: number;
  pendingFees: number;
  pendingFeesAmount: number;
  totalClasses: number;
  todayAttendance?: number;
}

interface Announcement {
  id: number;
  title: string;
  content: string;
  target_audience: string;
  created_by: number;
  author: {
    id: number;
    email: string;
    profile_data: Record<string, unknown>;
  } | null;
  created_at: string;
  updated_at: string;
}

// Role-based stat card configuration
interface StatCardConfig {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  getValue: (stats: DashboardStats) => string | number;
  getSubtext?: (stats: DashboardStats) => string;
  href: string;
  roles: Array<User["role"]>;
  color: string;
}

const statCardConfigs: StatCardConfig[] = [
  {
    title: "Total Students",
    icon: GraduationCap,
    getValue: (stats) => stats.totalStudents,
    href: "/students",
    roles: ["admin", "teacher", "super_admin"],
    color: "text-blue-600",
  },
  {
    title: "Total Teachers",
    icon: Users,
    getValue: (stats) => stats.totalTeachers,
    href: "/teachers",
    roles: ["admin", "super_admin"],
    color: "text-green-600",
  },
  {
    title: "Pending Fees",
    icon: DollarSign,
    getValue: (stats) => stats.pendingFees,
    getSubtext: (stats) => `$${stats.pendingFeesAmount.toLocaleString()} total`,
    href: "/fees?status=pending",
    roles: ["admin", "super_admin"],
    color: "text-orange-600",
  },
  {
    title: "Total Classes",
    icon: BookOpen,
    getValue: (stats) => stats.totalClasses,
    href: "/classes",
    roles: ["admin", "teacher", "super_admin"],
    color: "text-purple-600",
  },
];

// Quick action configuration
interface QuickAction {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  roles: Array<User["role"]>;
  variant?: "default" | "outline";
}

const quickActions: QuickAction[] = [
  {
    title: "Add Student",
    description: "Register a new student",
    icon: Plus,
    href: "/students/new",
    roles: ["admin", "super_admin"],
  },
  {
    title: "Mark Attendance",
    description: "Record today's attendance",
    icon: ClipboardList,
    href: "/attendance/mark",
    roles: ["admin", "teacher", "super_admin"],
  },
  {
    title: "View Timetable",
    description: "Check class schedules",
    icon: Calendar,
    href: "/timetable",
    roles: ["admin", "teacher", "student", "parent", "super_admin"],
  },
  {
    title: "Create Announcement",
    description: "Post a new announcement",
    icon: Megaphone,
    href: "/announcements/new",
    roles: ["admin", "teacher", "super_admin"],
  },
  {
    title: "View Grades",
    description: "Check academic performance",
    icon: FileText,
    href: "/grades",
    roles: ["student", "parent"],
  },
  {
    title: "View Fees",
    description: "Check fee status",
    icon: DollarSign,
    href: "/fees",
    roles: ["student", "parent"],
  },
  {
    title: "Request Leave",
    description: "Submit a leave request",
    icon: Clock,
    href: "/leave-requests/new",
    roles: ["teacher", "student"],
  },
  {
    title: "Generate Reports",
    description: "View analytics and reports",
    icon: FileText,
    href: "/reports",
    roles: ["admin", "super_admin"],
  },
];

// Stat Card Component
function StatCard({ config, stats, isLoading }: { config: StatCardConfig; stats: DashboardStats | null; isLoading: boolean }) {
  const Icon = config.icon;

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-8 rounded" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-16 mb-1" />
          <Skeleton className="h-3 w-20" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Link href={config.href}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {config.title}
          </CardTitle>
          <Icon className={`h-5 w-5 ${config.color}`} />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {stats ? config.getValue(stats) : 0}
          </div>
          {config.getSubtext && stats && (
            <p className="text-xs text-muted-foreground mt-1">
              {config.getSubtext(stats)}
            </p>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

// Announcements Widget Component
function AnnouncementsWidget({ announcements, isLoading }: { announcements: Announcement[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Megaphone className="h-5 w-5" />
            Recent Announcements
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-1/4" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Megaphone className="h-5 w-5" />
            Recent Announcements
          </CardTitle>
          <CardDescription>Latest updates and notices</CardDescription>
        </div>
        <Link href="/announcements">
          <Button variant="ghost" size="sm" className="gap-1">
            View All
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        {announcements.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No announcements yet
          </p>
        ) : (
          <div className="space-y-4">
            {announcements.map((announcement) => (
              <div
                key={announcement.id}
                className="border-b last:border-0 pb-4 last:pb-0"
              >
                <h4 className="font-medium text-sm">{announcement.title}</h4>
                <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                  {announcement.content}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  {new Date(announcement.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Quick Actions Component
function QuickActionsWidget({ userRole }: { userRole: User["role"] }) {
  const filteredActions = quickActions.filter((action) =>
    action.roles.includes(userRole)
  );

  // Take only first 4 actions for the widget
  const displayActions = filteredActions.slice(0, 4);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
        <CardDescription>Common tasks for your role</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          {displayActions.map((action) => {
            const Icon = action.icon;
            return (
              <Link key={action.href} href={action.href}>
                <Button
                  variant="outline"
                  className="w-full h-auto flex flex-col items-center gap-2 py-4 hover:bg-accent"
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-xs font-medium">{action.title}</span>
                </Button>
              </Link>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// Main Dashboard Page
export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [isLoadingAnnouncements, setIsLoadingAnnouncements] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter stat cards based on user role
  const visibleStatCards = statCardConfigs.filter((config) =>
    user ? config.roles.includes(user.role) : false
  );

  // Fetch dashboard stats
  useEffect(() => {
    async function fetchStats() {
      if (!user) return;

      setIsLoadingStats(true);
      try {
        // Fetch stats based on role
        const statsData: DashboardStats = {
          totalStudents: 0,
          totalTeachers: 0,
          pendingFees: 0,
          pendingFeesAmount: 0,
          totalClasses: 0,
        };

        // Admins and teachers can see student count
        if (["admin", "teacher", "super_admin"].includes(user.role)) {
          try {
            const studentsResponse = await api.get<{ total_count: number }>("/api/students", { page_size: 1 });
            statsData.totalStudents = studentsResponse?.total_count || 0;
          } catch {
            // Silently fail for individual stats
          }
        }

        // Only admins can see teacher count
        if (["admin", "super_admin"].includes(user.role)) {
          try {
            const teachersResponse = await api.get<{ total_count: number }>("/api/teachers", { page_size: 1 });
            statsData.totalTeachers = teachersResponse?.total_count || 0;
          } catch {
            // Silently fail for individual stats
          }
        }

        // Admins can see pending fees
        if (["admin", "super_admin"].includes(user.role)) {
          try {
            const feesResponse = await api.get<{ total_count: number; total_pending_amount: number }>("/api/fees/pending", { page_size: 1 });
            statsData.pendingFees = feesResponse?.total_count || 0;
            statsData.pendingFeesAmount = feesResponse?.total_pending_amount || 0;
          } catch {
            // Silently fail for individual stats
          }
        }

        // Admins and teachers can see class count
        if (["admin", "teacher", "super_admin"].includes(user.role)) {
          try {
            const classesResponse = await api.get<{ total_count: number }>("/api/classes", { page_size: 1 });
            statsData.totalClasses = classesResponse?.total_count || 0;
          } catch {
            // Silently fail for individual stats
          }
        }

        setStats(statsData);
      } catch (err) {
        const apiError = err as ApiError;
        setError(apiError.message || "Failed to load dashboard stats");
      } finally {
        setIsLoadingStats(false);
      }
    }

    fetchStats();
  }, [user]);

  // Fetch recent announcements
  useEffect(() => {
    async function fetchAnnouncements() {
      if (!user) return;

      setIsLoadingAnnouncements(true);
      try {
        const response = await api.get<Announcement[] | { items: Announcement[] }>("/api/announcements/recent", { limit: 5 });
        // Handle both array response and object with items array
        if (Array.isArray(response)) {
          setAnnouncements(response);
        } else if (response && Array.isArray(response.items)) {
          setAnnouncements(response.items);
        } else {
          setAnnouncements([]);
        }
      } catch (err) {
        // Silently fail for announcements - not critical
        console.error("Failed to fetch announcements:", err);
        setAnnouncements([]);
      } finally {
        setIsLoadingAnnouncements(false);
      }
    }

    fetchAnnouncements();
  }, [user]);

  // Get greeting based on time of day
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  // Get user display name
  const getUserName = () => {
    if (!user) return "";
    const firstName = user.profile_data?.first_name as string;
    if (firstName) return firstName;
    return user.email.split("@")[0];
  };

  if (!user) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">
          {getGreeting()}, {getUserName()}!
        </h1>
        <p className="text-muted-foreground">
          Here&apos;s what&apos;s happening in your school today.
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      {/* Stats Cards - Role-based */}
      {visibleStatCards.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {visibleStatCards.map((config) => (
            <StatCard
              key={config.title}
              config={config}
              stats={stats}
              isLoading={isLoadingStats}
            />
          ))}
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Recent Announcements */}
        <AnnouncementsWidget
          announcements={announcements}
          isLoading={isLoadingAnnouncements}
        />

        {/* Quick Actions */}
        <QuickActionsWidget userRole={user.role} />
      </div>
    </div>
  );
}
