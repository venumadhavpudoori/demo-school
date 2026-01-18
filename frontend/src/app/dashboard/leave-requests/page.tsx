"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Plus,
  ChevronLeft,
  ChevronRight,
  Eye,
  Filter,
  X,
  Calendar,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
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
interface UserInfo {
  id: number;
  email: string;
  profile_data: {
    first_name?: string;
    last_name?: string;
  };
}

interface LeaveRequestListItem {
  id: number;
  requester_id: number;
  requester_type: string;
  from_date: string;
  to_date: string;
  reason: string;
  status: string;
  approved_by: number | null;
  requester: UserInfo | null;
  created_at: string | null;
}

interface LeaveRequestListResponse {
  items: LeaveRequestListItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-800",
};

const statusIcons: Record<string, React.ReactNode> = {
  pending: <Clock className="h-3 w-3" />,
  approved: <CheckCircle className="h-3 w-3" />,
  rejected: <XCircle className="h-3 w-3" />,
  cancelled: <AlertCircle className="h-3 w-3" />,
};

const requesterTypeLabels: Record<string, string> = {
  teacher: "Teacher",
  student: "Student",
};

export default function LeaveRequestsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  // State
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequestListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state from URL params
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");
  const status = searchParams.get("status") || "";
  const requesterType = searchParams.get("requester_type") || "";
  const viewMode = searchParams.get("view") || "my"; // "my" or "all" (admin only)

  // Local filter state
  const [statusFilter, setStatusFilter] = useState(status);
  const [requesterTypeFilter, setRequesterTypeFilter] = useState(requesterType);

  // Check permissions
  const isAdmin = user?.role === "admin" || user?.role === "super_admin";
  const canCreateLeaveRequest = user?.role === "teacher" || user?.role === "student" || isAdmin;

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
      if (!("page" in newFilters)) {
        params.set("page", "1");
      }
      router.push(`/dashboard/leave-requests?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Fetch leave requests
  useEffect(() => {
    async function fetchLeaveRequests() {
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {
          page,
          page_size: pageSize,
        };
        if (status) params.status = status;
        if (requesterType) params.requester_type = requesterType;

        // Use different endpoint based on view mode
        const endpoint = isAdmin && viewMode === "all" 
          ? "/api/leave-requests" 
          : "/api/leave-requests/my";

        const response = await api.get<LeaveRequestListResponse>(endpoint, params);
        setLeaveRequests(response.items);
        setTotalCount(response.total_count);
        setTotalPages(response.total_pages);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch leave requests");
      } finally {
        setIsLoading(false);
      }
    }
    fetchLeaveRequests();
  }, [page, pageSize, status, requesterType, viewMode, isAdmin]);

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({
      status: statusFilter,
      requester_type: requesterTypeFilter,
    });
    setShowFilters(false);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setStatusFilter("");
    setRequesterTypeFilter("");
    router.push("/dashboard/leave-requests");
  };

  // Toggle view mode (admin only)
  const toggleViewMode = () => {
    updateFilters({ view: viewMode === "my" ? "all" : "my" });
  };

  // Get requester name
  const getRequesterName = (requester: UserInfo | null) => {
    if (!requester) return "Unknown";
    if (requester.profile_data?.first_name || requester.profile_data?.last_name) {
      return `${requester.profile_data.first_name || ""} ${requester.profile_data.last_name || ""}`.trim();
    }
    return requester.email;
  };

  // Format date
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  // Calculate duration
  const calculateDuration = (fromDate: string, toDate: string) => {
    const from = new Date(fromDate);
    const to = new Date(toDate);
    const diffTime = Math.abs(to.getTime() - from.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
    return diffDays === 1 ? "1 day" : `${diffDays} days`;
  };

  const hasActiveFilters = !!status || !!requesterType;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Leave Requests</h1>
          <p className="text-muted-foreground">
            {isAdmin && viewMode === "all" 
              ? "Manage all leave requests" 
              : "View and manage your leave requests"}
          </p>
        </div>
        {canCreateLeaveRequest && (
          <Link href="/dashboard/leave-requests/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Request
            </Button>
          </Link>
        )}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {totalCount} request{totalCount !== 1 ? "s" : ""}
              </span>
              {isAdmin && (
                <Button
                  variant={viewMode === "all" ? "default" : "outline"}
                  size="sm"
                  onClick={toggleViewMode}
                  className="ml-4"
                >
                  {viewMode === "all" ? "All Requests" : "My Requests"}
                </Button>
              )}
            </div>

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
              <div className="grid gap-4 md:grid-cols-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">Status</label>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Statuses</option>
                    <option value="pending">Pending</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>
                {isAdmin && viewMode === "all" && (
                  <div>
                    <label className="text-sm font-medium mb-2 block">Requester Type</label>
                    <select
                      value={requesterTypeFilter}
                      onChange={(e) => setRequesterTypeFilter(e.target.value)}
                      className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                    >
                      <option value="">All Types</option>
                      <option value="teacher">Teacher</option>
                      <option value="student">Student</option>
                    </select>
                  </div>
                )}
                <div className="flex items-end">
                  <Button onClick={handleApplyFilters}>Apply Filters</Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Leave Requests Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            {isAdmin && viewMode === "all" ? "All Leave Requests" : "My Leave Requests"}
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
          ) : leaveRequests.length === 0 ? (
            <div className="text-center py-12">
              <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No leave requests found</p>
              {canCreateLeaveRequest && (
                <Link href="/dashboard/leave-requests/new">
                  <Button variant="link" className="mt-2">
                    Create your first leave request
                  </Button>
                </Link>
              )}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    {isAdmin && viewMode === "all" && <TableHead>Requester</TableHead>}
                    <TableHead>Type</TableHead>
                    <TableHead>From</TableHead>
                    <TableHead>To</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leaveRequests.map((request) => (
                    <TableRow key={request.id}>
                      {isAdmin && viewMode === "all" && (
                        <TableCell>
                          <p className="font-medium">{getRequesterName(request.requester)}</p>
                        </TableCell>
                      )}
                      <TableCell>
                        <Badge variant="outline">
                          {requesterTypeLabels[request.requester_type] || request.requester_type}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatDate(request.from_date)}</TableCell>
                      <TableCell>{formatDate(request.to_date)}</TableCell>
                      <TableCell>{calculateDuration(request.from_date, request.to_date)}</TableCell>
                      <TableCell>
                        <p className="text-sm text-muted-foreground max-w-[200px] truncate">
                          {request.reason}
                        </p>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={`${statusColors[request.status] || ""} gap-1`}
                        >
                          {statusIcons[request.status]}
                          {request.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Link href={`/dashboard/leave-requests/${request.id}`}>
                          <Button variant="ghost" size="icon-sm">
                            <Eye className="h-4 w-4" />
                          </Button>
                        </Link>
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
