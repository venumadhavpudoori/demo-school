"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Filter,
  X,
  Check,
  Clock,
  AlertCircle,
  Pencil,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
interface ClassItem {
  id: number;
  name: string;
  grade_level: number;
  academic_year: string;
}

interface SectionItem {
  id: number;
  class_id: number;
  name: string;
}

interface AttendanceListItem {
  id: number;
  student_id: number;
  student_name: string | null;
  class_id: number;
  class_name: string | null;
  date: string;
  status: string;
  remarks: string | null;
  marked_by: number | null;
}

interface AttendanceListResponse {
  items: AttendanceListItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

interface ClassListResponse {
  items: ClassItem[];
  total_count: number;
}

interface SectionListResponse {
  items: SectionItem[];
  total_count: number;
}

const statusConfig: Record<string, { label: string; color: string; icon: React.ComponentType<{ className?: string }> }> = {
  present: { label: "Present", color: "bg-green-100 text-green-800", icon: Check },
  absent: { label: "Absent", color: "bg-red-100 text-red-800", icon: X },
  late: { label: "Late", color: "bg-yellow-100 text-yellow-800", icon: Clock },
  half_day: { label: "Half Day", color: "bg-orange-100 text-orange-800", icon: AlertCircle },
  excused: { label: "Excused", color: "bg-blue-100 text-blue-800", icon: AlertCircle },
};

export default function AttendanceHistoryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  // State
  const [attendance, setAttendance] = useState<AttendanceListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [sections, setSections] = useState<SectionItem[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state from URL params
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");
  const classId = searchParams.get("class_id") || "";
  const sectionId = searchParams.get("section_id") || "";
  const status = searchParams.get("status") || "";
  const startDate = searchParams.get("start_date") || "";
  const endDate = searchParams.get("end_date") || "";

  // Local filter state for inputs
  const [classFilter, setClassFilter] = useState(classId);
  const [sectionFilter, setSectionFilter] = useState(sectionId);
  const [statusFilter, setStatusFilter] = useState(status);
  const [startDateFilter, setStartDateFilter] = useState(startDate);
  const [endDateFilter, setEndDateFilter] = useState(endDate);

  // Check permissions
  const canEditAttendance = user?.role === "admin" || user?.role === "super_admin" || user?.role === "teacher";

  // Update URL with filters
  const updateFilters = useCallback(
    (newFilters: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());
      Object.entries(newFilters).forEach(([key, value]) => {
        if (value) {
          params.set(key, value);
        } else {
          params.delete(key);
        }
      });
      // Reset to page 1 when filters change (except when changing page)
      if (!("page" in newFilters)) {
        params.set("page", "1");
      }
      router.push(`/attendance/history?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Fetch classes for filter dropdown
  useEffect(() => {
    async function fetchClasses() {
      try {
        const response = await api.get<ClassListResponse>("/api/classes", {
          page_size: 100,
        });
        setClasses(response.items);
      } catch (err) {
        console.error("Failed to fetch classes:", err);
      }
    }
    fetchClasses();
  }, []);

  // Fetch sections when class changes
  useEffect(() => {
    async function fetchSections() {
      if (!classFilter) {
        setSections([]);
        return;
      }
      try {
        const response = await api.get<SectionListResponse>("/api/sections", {
          class_id: parseInt(classFilter),
          page_size: 100,
        });
        setSections(response.items);
      } catch (err) {
        console.error("Failed to fetch sections:", err);
      }
    }
    fetchSections();
  }, [classFilter]);

  // Fetch attendance records
  useEffect(() => {
    async function fetchAttendance() {
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {
          page,
          page_size: pageSize,
        };
        if (classId) params.class_id = parseInt(classId);
        if (sectionId) params.section_id = parseInt(sectionId);
        if (status) params.status = status;
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;

        const response = await api.get<AttendanceListResponse>("/api/attendance", params);
        setAttendance(response.items);
        setTotalCount(response.total_count);
        setTotalPages(response.total_pages);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch attendance records");
      } finally {
        setIsLoading(false);
      }
    }
    fetchAttendance();
  }, [page, pageSize, classId, sectionId, status, startDate, endDate]);

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({
      class_id: classFilter,
      section_id: sectionFilter,
      status: statusFilter,
      start_date: startDateFilter,
      end_date: endDateFilter,
    });
    setShowFilters(false);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setClassFilter("");
    setSectionFilter("");
    setStatusFilter("");
    setStartDateFilter("");
    setEndDateFilter("");
    router.push("/attendance/history");
  };

  // Check if any filters are active
  const hasActiveFilters = classId || sectionId || status || startDate || endDate;

  // Format date for display
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Attendance History</h1>
          <p className="text-muted-foreground">
            View and filter attendance records
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/attendance">
            <Button>
              <Calendar className="h-4 w-4 mr-2" />
              Mark Attendance
            </Button>
          </Link>
          <Link href="/attendance/report">
            <Button variant="outline">
              View Reports
            </Button>
          </Link>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            {/* Date Range Quick Select */}
            <div className="flex gap-2 flex-wrap">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = new Date().toISOString().split("T")[0];
                  updateFilters({ start_date: today, end_date: today });
                }}
              >
                Today
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const weekAgo = new Date(today);
                  weekAgo.setDate(weekAgo.getDate() - 7);
                  updateFilters({
                    start_date: weekAgo.toISOString().split("T")[0],
                    end_date: today.toISOString().split("T")[0],
                  });
                }}
              >
                Last 7 Days
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const monthAgo = new Date(today);
                  monthAgo.setDate(monthAgo.getDate() - 30);
                  updateFilters({
                    start_date: monthAgo.toISOString().split("T")[0],
                    end_date: today.toISOString().split("T")[0],
                  });
                }}
              >
                Last 30 Days
              </Button>
            </div>

            {/* Filter Toggle */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                className={showFilters ? "bg-accent" : ""}
              >
                <Filter className="h-4 w-4 mr-2" />
                Filters
                {hasActiveFilters && (
                  <Badge variant="secondary" className="ml-2">
                    Active
                  </Badge>
                )}
              </Button>
              {hasActiveFilters && (
                <Button variant="ghost" onClick={handleClearFilters}>
                  <X className="h-4 w-4 mr-2" />
                  Clear
                </Button>
              )}
            </div>
          </div>

          {/* Filter Panel */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t">
              <div className="grid gap-4 md:grid-cols-6">
                <div>
                  <label className="text-sm font-medium mb-2 block">Start Date</label>
                  <input
                    type="date"
                    value={startDateFilter}
                    onChange={(e) => setStartDateFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">End Date</label>
                  <input
                    type="date"
                    value={endDateFilter}
                    onChange={(e) => setEndDateFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Class</label>
                  <select
                    value={classFilter}
                    onChange={(e) => {
                      setClassFilter(e.target.value);
                      setSectionFilter("");
                    }}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Classes</option>
                    {classes.map((cls) => (
                      <option key={cls.id} value={cls.id}>
                        {cls.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Section</label>
                  <select
                    value={sectionFilter}
                    onChange={(e) => setSectionFilter(e.target.value)}
                    disabled={!classFilter}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm disabled:opacity-50"
                  >
                    <option value="">All Sections</option>
                    {sections.map((section) => (
                      <option key={section.id} value={section.id}>
                        {section.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Status</label>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Statuses</option>
                    <option value="present">Present</option>
                    <option value="absent">Absent</option>
                    <option value="late">Late</option>
                    <option value="half_day">Half Day</option>
                    <option value="excused">Excused</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <Button onClick={handleApplyFilters} className="w-full">
                    Apply Filters
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Attendance Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Attendance Records</span>
            <span className="text-sm font-normal text-muted-foreground">
              {totalCount} record{totalCount !== 1 ? "s" : ""} found
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-24" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                  <Skeleton className="h-8 w-20" />
                </div>
              ))}
            </div>
          ) : attendance.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No attendance records found</p>
              {hasActiveFilters && (
                <Button
                  variant="link"
                  onClick={handleClearFilters}
                  className="mt-2"
                >
                  Clear filters
                </Button>
              )}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Student</TableHead>
                    <TableHead>Class</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Remarks</TableHead>
                    {canEditAttendance && (
                      <TableHead className="text-right">Actions</TableHead>
                    )}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {attendance.map((record) => {
                    const config = statusConfig[record.status] || statusConfig.present;
                    const StatusIcon = config.icon;
                    return (
                      <TableRow key={record.id}>
                        <TableCell className="font-medium">
                          {formatDate(record.date)}
                        </TableCell>
                        <TableCell>
                          {record.student_name || `Student #${record.student_id}`}
                        </TableCell>
                        <TableCell>
                          {record.class_name || `Class #${record.class_id}`}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="secondary"
                            className={`${config.color} flex items-center gap-1 w-fit`}
                          >
                            <StatusIcon className="h-3 w-3" />
                            {config.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-xs truncate">
                          {record.remarks || "-"}
                        </TableCell>
                        {canEditAttendance && (
                          <TableCell className="text-right">
                            <Button variant="ghost" size="icon-sm">
                              <Pencil className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        )}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => updateFilters({ page: String(page - 1) })}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => updateFilters({ page: String(page + 1) })}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
