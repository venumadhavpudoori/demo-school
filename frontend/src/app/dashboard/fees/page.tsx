"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Search,
  Plus,
  ChevronLeft,
  ChevronRight,
  Eye,
  CreditCard,
  Filter,
  X,
  AlertCircle,
  DollarSign,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
interface FeeListItem {
  id: number;
  student_id: number;
  student_name: string | null;
  fee_type: string;
  amount: number;
  paid_amount: number;
  remaining: number;
  due_date: string;
  payment_date: string | null;
  status: string;
  academic_year: string;
}

interface FeeListResponse {
  items: FeeListItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

interface PendingFeeListResponse extends FeeListResponse {
  total_pending_amount: number;
}

interface StudentListItem {
  id: number;
  admission_number: string;
  user: {
    profile_data: {
      first_name?: string;
      last_name?: string;
    };
  } | null;
}

interface StudentListResponse {
  items: StudentListItem[];
  total_count: number;
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  partial: "bg-orange-100 text-orange-800",
  paid: "bg-green-100 text-green-800",
  overdue: "bg-red-100 text-red-800",
  waived: "bg-gray-100 text-gray-800",
};

const statusIcons: Record<string, React.ReactNode> = {
  pending: <AlertCircle className="h-3 w-3" />,
  partial: <DollarSign className="h-3 w-3" />,
  overdue: <AlertCircle className="h-3 w-3" />,
};

export default function FeesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  // State
  const [fees, setFees] = useState<FeeListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [totalPendingAmount, setTotalPendingAmount] = useState(0);
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state from URL params
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");
  const studentId = searchParams.get("student_id") || "";
  const status = searchParams.get("status") || "";
  const feeType = searchParams.get("fee_type") || "";
  const academicYear = searchParams.get("academic_year") || "";
  const showPendingOnly = searchParams.get("pending") === "true";

  // Local filter state for inputs
  const [studentFilter, setStudentFilter] = useState(studentId);
  const [statusFilter, setStatusFilter] = useState(status);
  const [feeTypeFilter, setFeeTypeFilter] = useState(feeType);
  const [academicYearFilter, setAcademicYearFilter] = useState(academicYear);

  // Check if user can manage fees
  const canManageFees = user?.role === "admin" || user?.role === "super_admin";

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
      router.push(`/dashboard/fees?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Fetch students for filter dropdown
  useEffect(() => {
    async function fetchStudents() {
      try {
        const response = await api.get<StudentListResponse>("/api/students", {
          page_size: 100,
        });
        setStudents(response.items);
      } catch (err) {
        console.error("Failed to fetch students:", err);
      }
    }
    fetchStudents();
  }, []);

  // Fetch fees
  useEffect(() => {
    async function fetchFees() {
      setIsLoading(true);
      try {
        const params: Record<string, string | number | boolean> = {
          page,
          page_size: pageSize,
        };
        if (studentId) params.student_id = parseInt(studentId);
        if (status) params.status = status;
        if (feeType) params.fee_type = feeType;
        if (academicYear) params.academic_year = academicYear;

        let response: FeeListResponse | PendingFeeListResponse;
        
        if (showPendingOnly) {
          response = await api.get<PendingFeeListResponse>("/api/fees/pending", params);
          setTotalPendingAmount((response as PendingFeeListResponse).total_pending_amount);
        } else {
          response = await api.get<FeeListResponse>("/api/fees", params);
          setTotalPendingAmount(0);
        }
        
        setFees(response.items);
        setTotalCount(response.total_count);
        setTotalPages(response.total_pages);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch fees");
      } finally {
        setIsLoading(false);
      }
    }
    fetchFees();
  }, [page, pageSize, studentId, status, feeType, academicYear, showPendingOnly]);

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({
      student_id: studentFilter,
      status: statusFilter,
      fee_type: feeTypeFilter,
      academic_year: academicYearFilter,
    });
    setShowFilters(false);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setStudentFilter("");
    setStatusFilter("");
    setFeeTypeFilter("");
    setAcademicYearFilter("");
    router.push("/dashboard/fees");
  };

  // Toggle pending only view
  const togglePendingOnly = () => {
    updateFilters({ pending: showPendingOnly ? "" : "true" });
  };

  // Get student display name
  const getStudentName = (student: StudentListItem) => {
    if (student.user?.profile_data) {
      const firstName = student.user.profile_data.first_name;
      const lastName = student.user.profile_data.last_name;
      if (firstName || lastName) {
        return `${firstName || ""} ${lastName || ""}`.trim();
      }
    }
    return student.admission_number;
  };

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount);
  };

  // Format date
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  // Check if fee is overdue
  const isOverdue = (fee: FeeListItem) => {
    if (fee.status === "paid" || fee.status === "waived") return false;
    return new Date(fee.due_date) < new Date();
  };

  // Check if any filters are active
  const hasActiveFilters = studentId || status || feeType || academicYear || showPendingOnly;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Fee Management</h1>
          <p className="text-muted-foreground">
            Manage student fees and payments
          </p>
        </div>
        {canManageFees && (
          <Link href="/dashboard/fees/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Fee
            </Button>
          </Link>
        )}
      </div>

      {/* Summary Cards */}
      {showPendingOnly && totalPendingAmount > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-orange-100 rounded-full">
                <AlertCircle className="h-6 w-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-orange-600 font-medium">Total Pending Amount</p>
                <p className="text-2xl font-bold text-orange-700">
                  {formatCurrency(totalPendingAmount)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            {/* Quick Actions */}
            <div className="flex gap-2">
              <Button
                variant={showPendingOnly ? "default" : "outline"}
                onClick={togglePendingOnly}
                className="gap-2"
              >
                <AlertCircle className="h-4 w-4" />
                Pending Fees
              </Button>
              {canManageFees && (
                <Link href="/dashboard/fees/report">
                  <Button variant="outline" className="gap-2">
                    <DollarSign className="h-4 w-4" />
                    Collection Report
                  </Button>
                </Link>
              )}
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
                  <label className="text-sm font-medium mb-2 block">Student</label>
                  <select
                    value={studentFilter}
                    onChange={(e) => setStudentFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Students</option>
                    {students.map((student) => (
                      <option key={student.id} value={student.id}>
                        {getStudentName(student)}
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
                    <option value="pending">Pending</option>
                    <option value="partial">Partial</option>
                    <option value="paid">Paid</option>
                    <option value="overdue">Overdue</option>
                    <option value="waived">Waived</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Fee Type</label>
                  <Input
                    placeholder="e.g., Tuition"
                    value={feeTypeFilter}
                    onChange={(e) => setFeeTypeFilter(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Academic Year</label>
                  <Input
                    placeholder="e.g., 2024-2025"
                    value={academicYearFilter}
                    onChange={(e) => setAcademicYearFilter(e.target.value)}
                  />
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

      {/* Fees Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>{showPendingOnly ? "Pending Fees" : "Fee Records"}</span>
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
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                  <Skeleton className="h-8 w-20" />
                </div>
              ))}
            </div>
          ) : fees.length === 0 ? (
            <div className="text-center py-12">
              <DollarSign className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No fee records found</p>
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
                    <TableHead>Student</TableHead>
                    <TableHead>Fee Type</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Paid</TableHead>
                    <TableHead>Remaining</TableHead>
                    <TableHead>Due Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {fees.map((fee) => (
                    <TableRow 
                      key={fee.id}
                      className={isOverdue(fee) ? "bg-red-50" : ""}
                    >
                      <TableCell>
                        <div>
                          <p className="font-medium">{fee.student_name || `Student #${fee.student_id}`}</p>
                          <p className="text-sm text-muted-foreground">
                            {fee.academic_year}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>{fee.fee_type}</TableCell>
                      <TableCell className="font-medium">
                        {formatCurrency(fee.amount)}
                      </TableCell>
                      <TableCell className="text-green-600">
                        {formatCurrency(fee.paid_amount)}
                      </TableCell>
                      <TableCell className={fee.remaining > 0 ? "text-orange-600 font-medium" : ""}>
                        {formatCurrency(fee.remaining)}
                      </TableCell>
                      <TableCell>
                        <span className={isOverdue(fee) ? "text-red-600 font-medium" : ""}>
                          {formatDate(fee.due_date)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={`${statusColors[fee.status] || ""} gap-1`}
                        >
                          {statusIcons[fee.status]}
                          {fee.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Link href={`/dashboard/fees/${fee.id}`}>
                            <Button variant="ghost" size="icon-sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                          {canManageFees && fee.status !== "paid" && fee.status !== "waived" && (
                            <Link href={`/dashboard/fees/${fee.id}/payment`}>
                              <Button variant="ghost" size="icon-sm" className="text-green-600">
                                <CreditCard className="h-4 w-4" />
                              </Button>
                            </Link>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
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
