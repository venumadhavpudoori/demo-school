"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Calendar,
  Users,
  TrendingUp,
  TrendingDown,
  Filter,
  X,
  Download,
  BarChart3,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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

interface ClassAttendanceSummary {
  total_days: number;
  total_students: number;
  total_records: number;
  present_count: number;
  absent_count: number;
  late_count: number;
  half_day_count: number;
  average_attendance_percentage: number;
}

interface StudentAttendanceSummary {
  student_id: number;
  student_name: string | null;
  total_days: number;
  present_days: number;
  absent_days: number;
  late_days: number;
  half_days: number;
  attendance_percentage: number;
}

interface AttendanceReportResponse {
  class_id: number | null;
  section_id: number | null;
  start_date: string | null;
  end_date: string | null;
  class_summary: ClassAttendanceSummary | null;
  student_summaries: StudentAttendanceSummary[];
  total_students: number;
}

interface ClassListResponse {
  items: ClassItem[];
  total_count: number;
}

interface SectionListResponse {
  items: SectionItem[];
  total_count: number;
}

// Progress bar component
function ProgressBar({ 
  value, 
  className = "",
  color = "bg-primary"
}: { 
  value: number; 
  className?: string;
  color?: string;
}) {
  return (
    <div className={`h-2 bg-muted rounded-full overflow-hidden ${className}`}>
      <div 
        className={`h-full ${color} transition-all duration-300`}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

// Get color based on percentage
function getPercentageColor(percentage: number): string {
  if (percentage >= 90) return "text-green-600";
  if (percentage >= 75) return "text-yellow-600";
  return "text-red-600";
}

function getProgressColor(percentage: number): string {
  if (percentage >= 90) return "bg-green-500";
  if (percentage >= 75) return "bg-yellow-500";
  return "bg-red-500";
}

export default function AttendanceReportPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  // State
  const [report, setReport] = useState<AttendanceReportResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [sections, setSections] = useState<SectionItem[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state from URL params
  const classId = searchParams.get("class_id") || "";
  const sectionId = searchParams.get("section_id") || "";
  const startDate = searchParams.get("start_date") || "";
  const endDate = searchParams.get("end_date") || "";

  // Local filter state for inputs
  const [classFilter, setClassFilter] = useState(classId);
  const [sectionFilter, setSectionFilter] = useState(sectionId);
  const [startDateFilter, setStartDateFilter] = useState(startDate);
  const [endDateFilter, setEndDateFilter] = useState(endDate);

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
      router.push(`/attendance/report?${params.toString()}`);
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

  // Fetch attendance report
  useEffect(() => {
    async function fetchReport() {
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {};
        if (classId) params.class_id = parseInt(classId);
        if (sectionId) params.section_id = parseInt(sectionId);
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;

        const response = await api.get<AttendanceReportResponse>("/api/attendance/report", params);
        setReport(response);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch attendance report");
      } finally {
        setIsLoading(false);
      }
    }
    fetchReport();
  }, [classId, sectionId, startDate, endDate]);

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({
      class_id: classFilter,
      section_id: sectionFilter,
      start_date: startDateFilter,
      end_date: endDateFilter,
    });
    setShowFilters(false);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setClassFilter("");
    setSectionFilter("");
    setStartDateFilter("");
    setEndDateFilter("");
    router.push("/attendance/report");
  };

  // Handle export
  const handleExport = async (format: "csv" | "pdf") => {
    setIsExporting(true);
    try {
      const response = await api.post<Blob>("/api/reports/export", {
        report_type: "attendance_summary",
        format,
        class_id: classId ? parseInt(classId) : null,
        section_id: sectionId ? parseInt(sectionId) : null,
        start_date: startDate || null,
        end_date: endDate || null,
      });

      if (format === "csv") {
        const blob = new Blob([response as unknown as string], { type: "text/csv" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `attendance_report_${new Date().toISOString().split("T")[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success("Report exported as CSV");
      } else {
        const blob = new Blob([JSON.stringify(response)], { type: "application/json" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `attendance_report_${new Date().toISOString().split("T")[0]}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success("Report data exported for PDF generation");
      }
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to export report");
    } finally {
      setIsExporting(false);
    }
  };

  // Check if any filters are active
  const hasActiveFilters = classId || sectionId || startDate || endDate;

  // Get class name
  const getClassName = () => {
    if (!classId) return "All Classes";
    const cls = classes.find((c) => c.id === parseInt(classId));
    return cls?.name || "Selected Class";
  };

  // Format date range
  const getDateRange = () => {
    if (startDate && endDate) {
      return `${new Date(startDate).toLocaleDateString()} - ${new Date(endDate).toLocaleDateString()}`;
    }
    if (startDate) return `From ${new Date(startDate).toLocaleDateString()}`;
    if (endDate) return `Until ${new Date(endDate).toLocaleDateString()}`;
    return "All Time";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Attendance Report</h1>
          <p className="text-muted-foreground">
            Analyze attendance patterns and statistics
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => handleExport("csv")}
            disabled={isExporting}
          >
            {isExporting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            Export CSV
          </Button>
          <Link href="/attendance">
            <Button variant="outline">
              <Calendar className="h-4 w-4 mr-2" />
              Mark Attendance
            </Button>
          </Link>
          <Link href="/attendance/history">
            <Button variant="outline">
              View History
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
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
                  updateFilters({
                    start_date: firstDay.toISOString().split("T")[0],
                    end_date: today.toISOString().split("T")[0],
                  });
                }}
              >
                This Month
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
              <div className="grid gap-4 md:grid-cols-5">
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

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <Skeleton className="h-4 w-24 mb-2" />
                  <Skeleton className="h-8 w-16" />
                </CardContent>
              </Card>
            ))}
          </div>
          <Card>
            <CardContent className="pt-6">
              <Skeleton className="h-64 w-full" />
            </CardContent>
          </Card>
        </div>
      ) : report ? (
        <>
          {/* Report Header */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                {getClassName()} - Attendance Summary
              </CardTitle>
              <CardDescription>{getDateRange()}</CardDescription>
            </CardHeader>
          </Card>

          {/* Summary Cards */}
          {report.class_summary && (
            <div className="grid gap-4 md:grid-cols-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Average Attendance</p>
                      <p className={`text-3xl font-bold ${getPercentageColor(report.class_summary.average_attendance_percentage)}`}>
                        {report.class_summary.average_attendance_percentage.toFixed(1)}%
                      </p>
                    </div>
                    {report.class_summary.average_attendance_percentage >= 75 ? (
                      <TrendingUp className="h-8 w-8 text-green-500" />
                    ) : (
                      <TrendingDown className="h-8 w-8 text-red-500" />
                    )}
                  </div>
                  <ProgressBar 
                    value={report.class_summary.average_attendance_percentage} 
                    color={getProgressColor(report.class_summary.average_attendance_percentage)}
                    className="mt-3"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Total Students</p>
                      <p className="text-3xl font-bold">{report.class_summary.total_students}</p>
                    </div>
                    <Users className="h-8 w-8 text-blue-500" />
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    {report.class_summary.total_days} days tracked
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Present</p>
                      <p className="text-3xl font-bold text-green-600">
                        {report.class_summary.present_count}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">Absent</p>
                      <p className="text-xl font-bold text-red-600">
                        {report.class_summary.absent_count}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-1 mt-3">
                    <div 
                      className="h-2 bg-green-500 rounded-l"
                      style={{ 
                        width: `${(report.class_summary.present_count / report.class_summary.total_records) * 100}%` 
                      }}
                    />
                    <div 
                      className="h-2 bg-red-500 rounded-r"
                      style={{ 
                        width: `${(report.class_summary.absent_count / report.class_summary.total_records) * 100}%` 
                      }}
                    />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Late</p>
                      <p className="text-3xl font-bold text-yellow-600">
                        {report.class_summary.late_count}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">Half Day</p>
                      <p className="text-xl font-bold text-orange-600">
                        {report.class_summary.half_day_count}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    {report.class_summary.total_records} total records
                  </p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Status Distribution Chart */}
          {report.class_summary && report.class_summary.total_records > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Attendance Distribution</CardTitle>
                <CardDescription>Breakdown by status</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[
                    { label: "Present", count: report.class_summary.present_count, color: "bg-green-500" },
                    { label: "Absent", count: report.class_summary.absent_count, color: "bg-red-500" },
                    { label: "Late", count: report.class_summary.late_count, color: "bg-yellow-500" },
                    { label: "Half Day", count: report.class_summary.half_day_count, color: "bg-orange-500" },
                  ].map((item) => {
                    const percentage = (item.count / report.class_summary!.total_records) * 100;
                    return (
                      <div key={item.label} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span>{item.label}</span>
                          <span className="text-muted-foreground">
                            {item.count} ({percentage.toFixed(1)}%)
                          </span>
                        </div>
                        <ProgressBar value={percentage} color={item.color} />
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Student-wise Report */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Student-wise Attendance</span>
                <span className="text-sm font-normal text-muted-foreground">
                  {report.student_summaries.length} student{report.student_summaries.length !== 1 ? "s" : ""}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {report.student_summaries.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-muted-foreground">No student data available</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Student</TableHead>
                      <TableHead className="text-center">Total Days</TableHead>
                      <TableHead className="text-center">Present</TableHead>
                      <TableHead className="text-center">Absent</TableHead>
                      <TableHead className="text-center">Late</TableHead>
                      <TableHead className="text-center">Half Day</TableHead>
                      <TableHead className="text-right">Attendance %</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.student_summaries.map((student) => (
                      <TableRow key={student.student_id}>
                        <TableCell className="font-medium">
                          {student.student_name || `Student #${student.student_id}`}
                        </TableCell>
                        <TableCell className="text-center">{student.total_days}</TableCell>
                        <TableCell className="text-center text-green-600 font-medium">
                          {student.present_days}
                        </TableCell>
                        <TableCell className="text-center text-red-600 font-medium">
                          {student.absent_days}
                        </TableCell>
                        <TableCell className="text-center text-yellow-600">
                          {student.late_days}
                        </TableCell>
                        <TableCell className="text-center text-orange-600">
                          {student.half_days}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <ProgressBar 
                              value={student.attendance_percentage} 
                              color={getProgressColor(student.attendance_percentage)}
                              className="w-16"
                            />
                            <span className={`font-medium ${getPercentageColor(student.attendance_percentage)}`}>
                              {student.attendance_percentage.toFixed(1)}%
                            </span>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-12">
              <p className="text-muted-foreground">No report data available</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
