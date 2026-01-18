"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Users,
  Filter,
  X,
  Download,
  Loader2,
  BarChart3,
  PieChart,
  AlertCircle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
interface FeeCollectionSummary {
  total_fees: number;
  total_amount: number;
  collected: number;
  pending: number;
  collection_percentage: number;
}

interface DefaulterStudent {
  student_id: number;
  student_name: string | null;
  fee_count: number;
  total_pending: number;
}

interface DefaultersInfo {
  count: number;
  total_pending_amount: number;
  students: DefaulterStudent[];
}

interface FeeCollectionResponse {
  report_type: string;
  filters: {
    academic_year: string | null;
    start_date: string | null;
    end_date: string | null;
    fee_type: string | null;
  };
  summary: FeeCollectionSummary;
  status_breakdown: Record<string, number>;
  fee_type_breakdown: Record<string, number>;
  defaulters: DefaultersInfo;
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

// Status colors for the chart
const statusColors: Record<string, string> = {
  paid: "bg-green-500",
  partial: "bg-yellow-500",
  pending: "bg-orange-500",
  overdue: "bg-red-500",
  waived: "bg-gray-400",
};

const statusLabels: Record<string, string> = {
  paid: "Paid",
  partial: "Partial",
  pending: "Pending",
  overdue: "Overdue",
  waived: "Waived",
};

// Get collection rate color
function getCollectionColor(percentage: number): string {
  if (percentage >= 90) return "text-green-600";
  if (percentage >= 70) return "text-yellow-600";
  return "text-red-600";
}

// Get progress bar color
function getProgressColor(percentage: number): string {
  if (percentage >= 90) return "bg-green-500";
  if (percentage >= 70) return "bg-yellow-500";
  return "bg-red-500";
}

// Format currency
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}

export default function FeeCollectionReportPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  // State
  const [report, setReport] = useState<FeeCollectionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [showFilters, setShowFilters] = useState(true);

  // Filter state from URL params
  const academicYear = searchParams.get("academic_year") || "";
  const startDate = searchParams.get("start_date") || "";
  const endDate = searchParams.get("end_date") || "";
  const feeType = searchParams.get("fee_type") || "";

  // Local filter state
  const [academicYearFilter, setAcademicYearFilter] = useState(academicYear);
  const [startDateFilter, setStartDateFilter] = useState(startDate);
  const [endDateFilter, setEndDateFilter] = useState(endDate);
  const [feeTypeFilter, setFeeTypeFilter] = useState(feeType);

  // Check if user can view reports (admin only)
  const canViewReports = user?.role === "admin" || user?.role === "super_admin";

  // Check if any filters are active
  const hasActiveFilters = academicYear || startDate || endDate || feeType;

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
      router.push(`/dashboard/fees/report?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Fetch report data
  useEffect(() => {
    async function fetchReport() {
      if (!canViewReports) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        const params: Record<string, string> = {};
        if (academicYear) params.academic_year = academicYear;
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;
        if (feeType) params.fee_type = feeType;

        const response = await api.get<FeeCollectionResponse>(
          "/api/reports/fee-collection",
          params
        );
        setReport(response);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch fee collection report");
        setReport(null);
      } finally {
        setIsLoading(false);
      }
    }
    fetchReport();
  }, [academicYear, startDate, endDate, feeType, canViewReports]);

  // Handle export
  const handleExport = async (format: "csv" | "pdf") => {
    setIsExporting(true);
    try {
      const response = await api.post<Blob>("/api/reports/export", {
        report_type: "fee_collection",
        format,
        academic_year: academicYear || null,
        start_date: startDate || null,
        end_date: endDate || null,
        fee_type: feeType || null,
      });

      // For CSV, trigger download
      if (format === "csv") {
        const blob = new Blob([response as unknown as BlobPart], { type: "text/csv" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `fee_collection_${new Date().toISOString().split("T")[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }

      toast.success(`Report exported as ${format.toUpperCase()}`);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to export report");
    } finally {
      setIsExporting(false);
    }
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setAcademicYearFilter("");
    setStartDateFilter("");
    setEndDateFilter("");
    setFeeTypeFilter("");
    router.push("/dashboard/fees/report");
  };

  // Handle apply filters
  const handleApplyFilters = () => {
    updateFilters({
      academic_year: academicYearFilter,
      start_date: startDateFilter,
      end_date: endDateFilter,
      fee_type: feeTypeFilter,
    });
  };

  // Get date range display
  const getDateRange = () => {
    if (startDate && endDate) {
      return `${new Date(startDate).toLocaleDateString()} - ${new Date(endDate).toLocaleDateString()}`;
    }
    if (startDate) return `From ${new Date(startDate).toLocaleDateString()}`;
    if (endDate) return `Until ${new Date(endDate).toLocaleDateString()}`;
    return "All Time";
  };

  // Permission check
  if (!canViewReports) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/fees">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-2xl font-bold">Fee Collection Report</h1>
        </div>
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">Access Denied</h3>
              <p className="text-muted-foreground">
                You don&apos;t have permission to view fee collection reports.
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
        <div className="flex items-center gap-4">
          <Link href="/dashboard/fees">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Fee Collection Report</h1>
            <p className="text-muted-foreground">
              Analyze fee collection and track defaulters
            </p>
          </div>
        </div>
        {report && (
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
          </div>
        )}
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Filter className="h-4 w-4" />
              Filters
            </CardTitle>
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={handleClearFilters}>
                <X className="h-4 w-4 mr-2" />
                Clear
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4 md:flex-row md:items-center mb-4">
            {/* Quick Date Range */}
            <div className="flex gap-2 flex-wrap">
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
                  const threeMonthsAgo = new Date(today);
                  threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
                  updateFilters({
                    start_date: threeMonthsAgo.toISOString().split("T")[0],
                    end_date: today.toISOString().split("T")[0],
                  });
                }}
              >
                Last 3 Months
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const today = new Date();
                  const firstDay = new Date(today.getFullYear(), 0, 1);
                  updateFilters({
                    start_date: firstDay.toISOString().split("T")[0],
                    end_date: today.toISOString().split("T")[0],
                  });
                }}
              >
                This Year
              </Button>
            </div>
          </div>

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
              <label className="text-sm font-medium mb-2 block">Academic Year</label>
              <input
                type="text"
                placeholder="e.g., 2024-2025"
                value={academicYearFilter}
                onChange={(e) => setAcademicYearFilter(e.target.value)}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Fee Type</label>
              <input
                type="text"
                placeholder="e.g., Tuition"
                value={feeTypeFilter}
                onChange={(e) => setFeeTypeFilter(e.target.value)}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
              />
            </div>
            <div className="flex items-end">
              <Button onClick={handleApplyFilters} className="w-full">
                Apply Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Loading State */}
      {isLoading && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <Skeleton className="h-4 w-24 mb-2" />
                <Skeleton className="h-8 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Report Content */}
      {!isLoading && report && (
        <>
          {/* Report Header */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Fee Collection Summary
              </CardTitle>
              <CardDescription>
                {getDateRange()}
                {academicYear && ` • Academic Year: ${academicYear}`}
                {feeType && ` • Fee Type: ${feeType}`}
              </CardDescription>
            </CardHeader>
          </Card>

          {/* Summary Cards */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <DollarSign className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Amount</p>
                    <p className="text-2xl font-bold">
                      {formatCurrency(report.summary.total_amount)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {report.summary.total_fees} fee records
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-green-100 rounded-lg">
                    <TrendingUp className="h-6 w-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Collected</p>
                    <p className="text-2xl font-bold text-green-600">
                      {formatCurrency(report.summary.collected)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-orange-100 rounded-lg">
                    <TrendingDown className="h-6 w-6 text-orange-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Pending</p>
                    <p className="text-2xl font-bold text-orange-600">
                      {formatCurrency(report.summary.pending)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div
                    className={`p-3 rounded-lg ${
                      report.summary.collection_percentage >= 70
                        ? "bg-green-100"
                        : "bg-red-100"
                    }`}
                  >
                    <PieChart
                      className={`h-6 w-6 ${
                        report.summary.collection_percentage >= 70
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Collection Rate</p>
                    <p
                      className={`text-2xl font-bold ${getCollectionColor(
                        report.summary.collection_percentage
                      )}`}
                    >
                      {report.summary.collection_percentage.toFixed(1)}%
                    </p>
                    <div className="mt-2">
                      <ProgressBar
                        value={report.summary.collection_percentage}
                        color={getProgressColor(report.summary.collection_percentage)}
                      />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Charts Row */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Status Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <PieChart className="h-5 w-5" />
                  Status Breakdown
                </CardTitle>
                <CardDescription>Fee records by payment status</CardDescription>
              </CardHeader>
              <CardContent>
                {Object.keys(report.status_breakdown).length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No status data available
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Object.entries(report.status_breakdown).map(([status, count]) => {
                      const total = Object.values(report.status_breakdown).reduce(
                        (sum, c) => sum + c,
                        0
                      );
                      const percentage = total > 0 ? (count / total) * 100 : 0;

                      return (
                        <div key={status} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="flex items-center gap-2">
                              <span
                                className={`w-3 h-3 rounded-full ${
                                  statusColors[status] || "bg-gray-400"
                                }`}
                              />
                              {statusLabels[status] || status}
                            </span>
                            <span className="text-muted-foreground">
                              {count} ({percentage.toFixed(1)}%)
                            </span>
                          </div>
                          <ProgressBar
                            value={percentage}
                            color={statusColors[status] || "bg-gray-400"}
                          />
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Fee Type Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Fee Type Breakdown
                </CardTitle>
                <CardDescription>Collection by fee type</CardDescription>
              </CardHeader>
              <CardContent>
                {Object.keys(report.fee_type_breakdown).length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No fee type data available
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Object.entries(report.fee_type_breakdown).map(
                      ([feeTypeName, amount]) => {
                        const total = report.summary.total_amount;
                        const percentage = total > 0 ? (amount / total) * 100 : 0;

                        return (
                          <div
                            key={feeTypeName}
                            className="p-3 bg-muted rounded-lg space-y-2"
                          >
                            <div className="flex justify-between items-center">
                              <span className="font-medium">{feeTypeName}</span>
                              <Badge variant="secondary">{formatCurrency(amount)}</Badge>
                            </div>
                            <ProgressBar value={percentage} />
                          </div>
                        );
                      }
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Defaulters Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-red-500" />
                Defaulters
                <Badge variant="destructive" className="ml-2">
                  {report.defaulters.count} students
                </Badge>
              </CardTitle>
              <CardDescription>
                Students with pending fee payments • Total pending:{" "}
                {formatCurrency(report.defaulters.total_pending_amount)}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {report.defaulters.students.length === 0 ? (
                <div className="text-center py-12">
                  <Users className="h-12 w-12 mx-auto text-green-500 mb-4" />
                  <p className="text-muted-foreground">
                    No defaulters found. All fees are up to date!
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Student</TableHead>
                      <TableHead className="text-center">Pending Fees</TableHead>
                      <TableHead className="text-right">Total Pending</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.defaulters.students.map((student, index) => (
                      <TableRow key={student.student_id}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div
                              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                                index < 3
                                  ? "bg-red-100 text-red-800"
                                  : "bg-muted"
                              }`}
                            >
                              {index + 1}
                            </div>
                            <div>
                              <span className="font-medium">
                                {student.student_name ||
                                  `Student #${student.student_id}`}
                              </span>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant="secondary">{student.fee_count}</Badge>
                        </TableCell>
                        <TableCell className="text-right font-medium text-red-600">
                          {formatCurrency(student.total_pending)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Link href={`/students/${student.student_id}`}>
                            <Button variant="ghost" size="sm">
                              View Profile
                            </Button>
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* No Data State */}
      {!isLoading && !report && (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <DollarSign className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No Report Data</h3>
              <p className="text-muted-foreground">
                Unable to load fee collection report. Please try again.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
