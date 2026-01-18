"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ChevronLeft,
  ChevronRight,
  Eye,
  CheckCircle,
  XCircle,
  Clock,
  Calendar,
  AlertCircle,
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
import { ConfirmDialog } from "@/components/ConfirmDialog";
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

interface PendingCountResponse {
  pending_count: number;
}

const requesterTypeLabels: Record<string, string> = {
  teacher: "Teacher",
  student: "Student",
};

export default function PendingLeaveRequestsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  // State
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequestListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);
  
  // Action state
  const [actionId, setActionId] = useState<number | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject" | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Filter state from URL params
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");

  // Check permissions
  const isAdmin = user?.role === "admin" || user?.role === "super_admin";

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
      router.push(`/dashboard/leave-requests/pending?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Fetch pending count
  useEffect(() => {
    async function fetchPendingCount() {
      if (!isAdmin) return;
      try {
        const response = await api.get<PendingCountResponse>("/api/leave-requests/pending/count");
        setPendingCount(response.pending_count);
      } catch (err) {
        console.error("Failed to fetch pending count:", err);
      }
    }
    fetchPendingCount();
  }, [isAdmin]);

  // Fetch pending leave requests
  useEffect(() => {
    async function fetchLeaveRequests() {
      if (!isAdmin) {
        router.push("/dashboard/leave-requests");
        return;
      }

      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {
          page,
          page_size: pageSize,
        };

        const response = await api.get<LeaveRequestListResponse>("/api/leave-requests/pending", params);
        setLeaveRequests(response.items);
        setTotalCount(response.total_count);
        setTotalPages(response.total_pages);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch pending leave requests");
      } finally {
        setIsLoading(false);
      }
    }
    fetchLeaveRequests();
  }, [page, pageSize, isAdmin, router]);

  // Handle approve/reject action
  const handleAction = async () => {
    if (!actionId || !actionType) return;

    setIsProcessing(true);
    try {
      const endpoint = actionType === "approve" 
        ? `/api/leave-requests/${actionId}/approve`
        : `/api/leave-requests/${actionId}/reject`;
      
      await api.post(endpoint);
      
      toast.success(`Leave request ${actionType === "approve" ? "approved" : "rejected"} successfully`);
      
      // Remove from list
      setLeaveRequests((prev) => prev.filter((r) => r.id !== actionId));
      setTotalCount((prev) => prev - 1);
      setPendingCount((prev) => prev - 1);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || `Failed to ${actionType} leave request`);
    } finally {
      setIsProcessing(false);
      setActionId(null);
      setActionType(null);
    }
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

  // Redirect non-admins
  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              You don&apos;t have permission to view this page.
            </p>
            <Link href="/dashboard/leave-requests">
              <Button variant="link">Go back to leave requests</Button>
            </Link>
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
          <h1 className="text-2xl font-bold">Pending Approvals</h1>
          <p className="text-muted-foreground">
            Review and approve or reject leave requests
          </p>
        </div>
        <Link href="/dashboard/leave-requests">
          <Button variant="outline">
            View All Requests
          </Button>
        </Link>
      </div>

      {/* Summary Card */}
      {pendingCount > 0 && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-yellow-100 rounded-full">
                <Clock className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-yellow-600 font-medium">Pending Requests</p>
                <p className="text-2xl font-bold text-yellow-700">
                  {pendingCount} request{pendingCount !== 1 ? "s" : ""} awaiting approval
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pending Requests Table */}
      <Card>
        <CardHeader>
          <CardTitle>Pending Leave Requests</CardTitle>
          <CardDescription>
            Review each request and approve or reject
          </CardDescription>
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
              <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-4" />
              <p className="text-muted-foreground">No pending leave requests</p>
              <p className="text-sm text-muted-foreground mt-1">
                All leave requests have been processed
              </p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Requester</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>From</TableHead>
                    <TableHead>To</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leaveRequests.map((request) => (
                    <TableRow key={request.id}>
                      <TableCell>
                        <p className="font-medium">{getRequesterName(request.requester)}</p>
                        <p className="text-sm text-muted-foreground">
                          {request.requester?.email}
                        </p>
                      </TableCell>
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
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Link href={`/dashboard/leave-requests/${request.id}`}>
                            <Button variant="ghost" size="icon-sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className="text-green-600 hover:text-green-700 hover:bg-green-50"
                            onClick={() => {
                              setActionId(request.id);
                              setActionType("approve");
                            }}
                          >
                            <CheckCircle className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => {
                              setActionId(request.id);
                              setActionType("reject");
                            }}
                          >
                            <XCircle className="h-4 w-4" />
                          </Button>
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

      {/* Approve Confirmation Dialog */}
      <ConfirmDialog
        open={actionType === "approve" && actionId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setActionId(null);
            setActionType(null);
          }
        }}
        title="Approve Leave Request"
        description="Are you sure you want to approve this leave request?"
        confirmLabel="Approve"
        onConfirm={handleAction}
        variant="default"
      />

      {/* Reject Confirmation Dialog */}
      <ConfirmDialog
        open={actionType === "reject" && actionId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setActionId(null);
            setActionType(null);
          }
        }}
        title="Reject Leave Request"
        description="Are you sure you want to reject this leave request?"
        confirmLabel="Reject"
        onConfirm={handleAction}
        variant="destructive"
      />
    </div>
  );
}
