"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BarChart3,
  Users,
  GraduationCap,
  DollarSign,
  Calendar,
  FileText,
  Download,
  Loader2,
  TrendingUp,
  TrendingDown,
  ClipboardList,
  PieChart,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types based on backend schema
interface ReportFilters {
  class_id: number | null;
  section_id: number | null;
  exam_id: number | null;
  subject_id: number | null;
  academic_year: string | null;
  start_date: string | null;
  end_date: string | null;
  fee_type: string | null;
}

interface AttendanceSummaryStats {
  total_students: number;
  average_attendance_percentage: number;
  total_days: number;
  total_records: number;
  present_count: number;
  absent_count: number;
  late_count: number;
  half_day_count: number;
}

interface GradeAnalysisSummary {
  class_id: number | null;
  class_name: string | null;
  exam_id: number | null;
  exam_name: string | null;
  total_students: number;
  total_grades: number | null;
  average_percentage: number;
  highest_percentage: number;
  lowest_percentage: number;
  pass_count: number;
  fail_count: number;
  pass_percentage: number;
}

interface FeeCollectionSummary {
  total_fees: number;
  total_amount: number;
  total_collected: number;
  total_pending: number;
  collection_percentage: number;
}

interface ComprehensiveReportResponse {
  report_type: string;
  filters: ReportFilters;
  attendance: AttendanceSummaryStats;
  grades: GradeAnalysisSummary;
  fees: FeeCollectionSummary;
}

// Report type configuration
interface ReportTypeConfig {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  color: string;
  bgColor: string;
}

const reportTypes: ReportTypeConfig[] = [
  {
    id: "attendance",
    title: "Attendance Report",
    description: "View attendance statistics, patterns, and student-wise breakdown",
    icon: ClipboardList,
    href: "/attendance/report",
    color: "text-blue-600",
    bgColor: "bg-blue-100",
  },
  {
    id: "grades",
    title: "Grade Analytics",
    description: "Analyze student performance, grade distribution, and rankings",
    icon: GraduationCap,
    href: "/grades/analytics",
    color: "text-purple-600",
    bgColor: "bg-purple-100",
  },
  {
    id: "fees",
    title: "Fee Collection Report",
    description: "Track fee collection, pending payments, and defaulters",
    icon: DollarSign,
    href: "/fees/report",
    color: "text-green-600",
    bgColor: "bg-green-100",
  },
];

// Format currency
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}

// Progress bar component
function ProgressBar({
  value,
  className = "",
  color = "bg-primary",
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
  if (percentage >= 70) return "text-yellow-600";
  return "text-red-600";
}

function getProgressColor(percentage: number): string {
  if (percentage >= 90) return "bg-green-500";
  if (percentage >= 70) return "bg-yellow-500";
  return "bg-red-500";
}

export default function ReportsDashboardPage() {
  const { user } = useAuth();
  const [comprehensiveReport, setComprehensiveReport] = useState<ComprehensiveReportResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState<string | null>(null);

  // Check if user can view reports (admin only)
  const canViewReports = user?.role === "admin" || user?.role === "super_admin";

  // Fetch comprehensive report for overview
  useEffect(() => {
    async function fetchComprehensiveReport() {
      if (!canViewReports) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        const response = await api.get<ComprehensiveReportResponse>("/api/reports/comprehensive");
        setComprehensiveReport(response);
      } catch (err) {
        const apiError = err as ApiError;
        console.error("Failed to fetch comprehensive report:", apiError);
        // Don't show error toast for permission issues
        if (apiError.status !== 403) {
          toast.error(apiError.message || "Failed to load report overview");
        }
      } finally {
        setIsLoading(false);
      }
    }

    fetchComprehensiveReport();
  }, [canViewReports]);

  // Handle export
  const handleExport = async (reportType: string, format: "csv" | "pdf") => {
    setIsExporting(`${reportType}-${format}`);
    try {
      const response = await api.post<Blob>("/api/reports/export", {
        report_type: reportType,
        format,
      });

      if (format === "csv") {
        const blob = new Blob([response as unknown as string], { type: "text/csv" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${reportType}_${new Date().toISOString().split("T")[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success(`Report exported as CSV`);
      } else {
        // For PDF, the backend returns JSON data for client-side PDF generation
        const blob = new Blob([JSON.stringify(response)], { type: "application/json" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${reportType}_${new Date().toISOString().split("T")[0]}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        toast.success(`Report data exported for PDF generation`);
      }
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to export report");
    } finally {
      setIsExporting(null);
    }
  };

  // Permission denied view
  if (!canViewReports) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Reports Dashboard</h1>
          <p className="text-muted-foreground">
            Access comprehensive reports and analytics
          </p>
        </div>
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">Access Denied</h3>
              <p className="text-muted-foreground">
                You don&apos;t have permission to view reports.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Reports Dashboard</h1>
          <p className="text-muted-foreground">
            Access comprehensive reports and analytics for your school
          </p>
        </div>
      </div>

      {/* Report Type Selection */}
      <div className="grid gap-4 md:grid-cols-3">
        {reportTypes.map((report) => {
          const Icon = report.icon;
          return (
            <Link key={report.id} href={report.href}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${report.bgColor}`}>
                      <Icon className={`h-5 w-5 ${report.color}`} />
                    </div>
                    <CardTitle className="text-lg">{report.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {report.description}
                  </p>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      {/* Quick Export Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Quick Export
          </CardTitle>
          <CardDescription>
            Export reports directly from here
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {/* Attendance Export */}
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <ClipboardList className="h-4 w-4 text-blue-600" />
                <span className="font-medium">Attendance Summary</span>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("attendance_summary", "csv")}
                  disabled={isExporting !== null}
                >
                  {isExporting === "attendance_summary-csv" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "CSV"
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("attendance_summary", "pdf")}
                  disabled={isExporting !== null}
                >
                  {isExporting === "attendance_summary-pdf" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "PDF Data"
                  )}
                </Button>
              </div>
            </div>

            {/* Grade Export */}
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <GraduationCap className="h-4 w-4 text-purple-600" />
                <span className="font-medium">Grade Analysis</span>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("grade_analysis", "csv")}
                  disabled={isExporting !== null}
                >
                  {isExporting === "grade_analysis-csv" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "CSV"
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("grade_analysis", "pdf")}
                  disabled={isExporting !== null}
                >
                  {isExporting === "grade_analysis-pdf" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "PDF Data"
                  )}
                </Button>
              </div>
            </div>

            {/* Fee Export */}
            <div className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <DollarSign className="h-4 w-4 text-green-600" />
                <span className="font-medium">Fee Collection</span>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("fee_collection", "csv")}
                  disabled={isExporting !== null}
                >
                  {isExporting === "fee_collection-csv" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "CSV"
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("fee_collection", "pdf")}
                  disabled={isExporting !== null}
                >
                  {isExporting === "fee_collection-pdf" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "PDF Data"
                  )}
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Overview Section */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Overview</h2>
        
        {isLoading ? (
          <div className="grid gap-6 md:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-4 w-32" />
                </CardHeader>
                <CardContent className="space-y-4">
                  <Skeleton className="h-8 w-24" />
                  <Skeleton className="h-2 w-full" />
                  <Skeleton className="h-4 w-40" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : comprehensiveReport ? (
          <div className="grid gap-6 md:grid-cols-3">
            {/* Attendance Overview */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <ClipboardList className="h-4 w-4 text-blue-600" />
                  Attendance Overview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-2xl font-bold">
                      {comprehensiveReport.attendance.average_attendance_percentage.toFixed(1)}%
                    </span>
                    {comprehensiveReport.attendance.average_attendance_percentage >= 75 ? (
                      <TrendingUp className="h-5 w-5 text-green-500" />
                    ) : (
                      <TrendingDown className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                  <ProgressBar
                    value={comprehensiveReport.attendance.average_attendance_percentage}
                    color={getProgressColor(comprehensiveReport.attendance.average_attendance_percentage)}
                  />
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>{comprehensiveReport.attendance.total_students} students</span>
                    <span>{comprehensiveReport.attendance.total_days} days tracked</span>
                  </div>
                  <Link href="/attendance/report">
                    <Button variant="outline" size="sm" className="w-full">
                      View Details
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            {/* Grades Overview */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <GraduationCap className="h-4 w-4 text-purple-600" />
                  Grades Overview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-2xl font-bold">
                      {comprehensiveReport.grades.pass_percentage.toFixed(1)}%
                    </span>
                    <Badge variant={comprehensiveReport.grades.pass_percentage >= 70 ? "default" : "destructive"}>
                      Pass Rate
                    </Badge>
                  </div>
                  <ProgressBar
                    value={comprehensiveReport.grades.pass_percentage}
                    color={getProgressColor(comprehensiveReport.grades.pass_percentage)}
                  />
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>Avg: {comprehensiveReport.grades.average_percentage.toFixed(1)}%</span>
                    <span>{comprehensiveReport.grades.total_students} students</span>
                  </div>
                  <Link href="/grades/analytics">
                    <Button variant="outline" size="sm" className="w-full">
                      View Details
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            {/* Fees Overview */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-green-600" />
                  Fee Collection Overview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-2xl font-bold">
                      {comprehensiveReport.fees.collection_percentage.toFixed(1)}%
                    </span>
                    <Badge variant={comprehensiveReport.fees.collection_percentage >= 70 ? "default" : "destructive"}>
                      Collected
                    </Badge>
                  </div>
                  <ProgressBar
                    value={comprehensiveReport.fees.collection_percentage}
                    color={getProgressColor(comprehensiveReport.fees.collection_percentage)}
                  />
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span className="text-green-600">{formatCurrency(comprehensiveReport.fees.total_collected)}</span>
                    <span className="text-orange-600">{formatCurrency(comprehensiveReport.fees.total_pending)} pending</span>
                  </div>
                  <Link href="/dashboard/fees/report">
                    <Button variant="outline" size="sm" className="w-full">
                      View Details
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <Card>
            <CardContent className="py-12">
              <div className="text-center">
                <PieChart className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No Data Available</h3>
                <p className="text-muted-foreground">
                  Report data will appear here once there is data in the system.
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Additional Stats */}
      {comprehensiveReport && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <Users className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Students</p>
                  <p className="text-2xl font-bold">{comprehensiveReport.attendance.total_students}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-100 rounded-lg">
                  <Calendar className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Days Tracked</p>
                  <p className="text-2xl font-bold">{comprehensiveReport.attendance.total_days}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-100 rounded-lg">
                  <FileText className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Fees</p>
                  <p className="text-2xl font-bold">{comprehensiveReport.fees.total_fees}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-orange-100 rounded-lg">
                  <DollarSign className="h-6 w-6 text-orange-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Amount</p>
                  <p className="text-2xl font-bold">{formatCurrency(comprehensiveReport.fees.total_amount)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
