"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Edit,
  Trash2,
  Calendar,
  User,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Ban,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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

interface LeaveRequestResponse {
  id: number;
  requester_id: number;
  requester_type: string;
  from_date: string;
  to_date: string;
  reason: string;
  status: string;
  approved_by: number | null;
  requester: UserInfo | null;
  approver: UserInfo | null;
  created_at: string | null;
  updated_at: string | null;
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-800",
};

const statusIcons: Record<string, React.ReactNode> = {
  pending: <Clock className="h-4 w-4" />,
  approved: <CheckCircle className="h-4 w-4" />,
  rejected: <XCircle className="h-4 w-4" />,
  cancelled: <AlertCircle className="h-4 w-4" />,
};

const requesterTypeLabels: Record<string, string> = {
  teacher: "Teacher",
  student: "Student",
};

export default function LeaveRequestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const leaveRequestId = params.id as string;

  const [leaveRequest, setLeaveRequest] = useState<LeaveRequestResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [showApproveDialog, setShowApproveDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);

  // Check permissions
  const isAdmin = user?.role === "admin" || user?.role === "super_admin";
  const isOwner = leaveRequest?.requester_id === user?.id;
  const canEdit = isOwner && leaveRequest?.status === "pending";
  const canDelete = (isOwner || isAdmin) && leaveRequest?.status === "pending";
  const canCancel = isOwner && (leaveRequest?.status === "pending" || leaveRequest?.status === "approved");
  const canApproveReject = isAdmin && leaveRequest?.status === "pending";

  // Fetch leave request
  useEffect(() => {
    async function fetchLeaveRequest() {
      setIsLoading(true);
      try {
        const response = await api.get<LeaveRequestResponse>(`/api/leave-requests/${leaveRequestId}`);
        setLeaveRequest(response);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch leave request");
        router.push("/dashboard/leave-requests");
      } finally {
        setIsLoading(false);
      }
    }
    fetchLeaveRequest();
  }, [leaveRequestId, router]);

  // Handle delete
  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.delete(`/api/leave-requests/${leaveRequestId}`);
      toast.success("Leave request deleted successfully");
      router.push("/dashboard/leave-requests");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to delete leave request");
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  // Handle cancel
  const handleCancel = async () => {
    setIsCancelling(true);
    try {
      await api.post(`/api/leave-requests/${leaveRequestId}/cancel`);
      toast.success("Leave request cancelled successfully");
      // Refresh the data
      const response = await api.get<LeaveRequestResponse>(`/api/leave-requests/${leaveRequestId}`);
      setLeaveRequest(response);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to cancel leave request");
    } finally {
      setIsCancelling(false);
      setShowCancelDialog(false);
    }
  };

  // Handle approve
  const handleApprove = async () => {
    setIsApproving(true);
    try {
      await api.post(`/api/leave-requests/${leaveRequestId}/approve`);
      toast.success("Leave request approved successfully");
      // Refresh the data
      const response = await api.get<LeaveRequestResponse>(`/api/leave-requests/${leaveRequestId}`);
      setLeaveRequest(response);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to approve leave request");
    } finally {
      setIsApproving(false);
      setShowApproveDialog(false);
    }
  };

  // Handle reject
  const handleReject = async () => {
    setIsRejecting(true);
    try {
      await api.post(`/api/leave-requests/${leaveRequestId}/reject`);
      toast.success("Leave request rejected successfully");
      // Refresh the data
      const response = await api.get<LeaveRequestResponse>(`/api/leave-requests/${leaveRequestId}`);
      setLeaveRequest(response);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to reject leave request");
    } finally {
      setIsRejecting(false);
      setShowRejectDialog(false);
    }
  };

  // Get user name
  const getUserName = (userInfo: UserInfo | null) => {
    if (!userInfo) return "Unknown";
    if (userInfo.profile_data?.first_name || userInfo.profile_data?.last_name) {
      return `${userInfo.profile_data.first_name || ""} ${userInfo.profile_data.last_name || ""}`.trim();
    }
    return userInfo.email;
  };

  // Format date
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  // Format datetime
  const formatDateTime = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
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

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!leaveRequest) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/leave-requests">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Leave Request Details</h1>
            <p className="text-muted-foreground">
              {requesterTypeLabels[leaveRequest.requester_type]} Leave Request
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {canApproveReject && (
            <>
              <Button
                variant="outline"
                className="text-green-600 hover:text-green-700 hover:bg-green-50"
                onClick={() => setShowApproveDialog(true)}
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Approve
              </Button>
              <Button
                variant="outline"
                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                onClick={() => setShowRejectDialog(true)}
              >
                <XCircle className="h-4 w-4 mr-2" />
                Reject
              </Button>
            </>
          )}
          {canEdit && (
            <Link href={`/dashboard/leave-requests/${leaveRequestId}/edit`}>
              <Button variant="outline">
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
            </Link>
          )}
          {canCancel && (
            <Button
              variant="outline"
              className="text-orange-600 hover:text-orange-700"
              onClick={() => setShowCancelDialog(true)}
            >
              <Ban className="h-4 w-4 mr-2" />
              Cancel Request
            </Button>
          )}
          {canDelete && (
            <Button
              variant="outline"
              className="text-red-600 hover:text-red-700"
              onClick={() => setShowDeleteDialog(true)}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          )}
        </div>
      </div>

      {/* Status Card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-full ${statusColors[leaveRequest.status]}`}>
                {statusIcons[leaveRequest.status]}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <p className="text-lg font-semibold capitalize">{leaveRequest.status}</p>
              </div>
            </div>
            <Badge
              variant="secondary"
              className={`${statusColors[leaveRequest.status]} text-sm px-3 py-1`}
            >
              {leaveRequest.status}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Leave Details */}
      <Card>
        <CardHeader>
          <CardTitle>Leave Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Date Range */}
          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex items-start gap-3">
              <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm text-muted-foreground">From Date</p>
                <p className="font-medium">{formatDate(leaveRequest.from_date)}</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm text-muted-foreground">To Date</p>
                <p className="font-medium">{formatDate(leaveRequest.to_date)}</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Clock className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>
                <p className="text-sm text-muted-foreground">Duration</p>
                <p className="font-medium">{calculateDuration(leaveRequest.from_date, leaveRequest.to_date)}</p>
              </div>
            </div>
          </div>

          {/* Reason */}
          <div>
            <p className="text-sm text-muted-foreground mb-2">Reason</p>
            <p className="whitespace-pre-wrap bg-muted p-4 rounded-md">{leaveRequest.reason}</p>
          </div>

          {/* Requester Info */}
          <div className="border-t pt-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="flex items-center gap-2 text-sm">
                <User className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Requested by:</span>
                <span className="font-medium">{getUserName(leaveRequest.requester)}</span>
              </div>
              {leaveRequest.approver && (
                <div className="flex items-center gap-2 text-sm">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    {leaveRequest.status === "approved" ? "Approved by:" : "Rejected by:"}
                  </span>
                  <span className="font-medium">{getUserName(leaveRequest.approver)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Timestamps */}
          <div className="border-t pt-4">
            <div className="grid gap-4 md:grid-cols-2 text-sm text-muted-foreground">
              <div>Created: {formatDateTime(leaveRequest.created_at)}</div>
              {leaveRequest.updated_at && leaveRequest.updated_at !== leaveRequest.created_at && (
                <div>Updated: {formatDateTime(leaveRequest.updated_at)}</div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Leave Request"
        description="Are you sure you want to delete this leave request? This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={handleDelete}
        variant="destructive"
      />

      {/* Cancel Confirmation Dialog */}
      <ConfirmDialog
        open={showCancelDialog}
        onOpenChange={setShowCancelDialog}
        title="Cancel Leave Request"
        description="Are you sure you want to cancel this leave request?"
        confirmLabel="Cancel Request"
        onConfirm={handleCancel}
        variant="destructive"
      />

      {/* Approve Confirmation Dialog */}
      <ConfirmDialog
        open={showApproveDialog}
        onOpenChange={setShowApproveDialog}
        title="Approve Leave Request"
        description="Are you sure you want to approve this leave request?"
        confirmLabel="Approve"
        onConfirm={handleApprove}
        variant="default"
      />

      {/* Reject Confirmation Dialog */}
      <ConfirmDialog
        open={showRejectDialog}
        onOpenChange={setShowRejectDialog}
        title="Reject Leave Request"
        description="Are you sure you want to reject this leave request?"
        confirmLabel="Reject"
        onConfirm={handleReject}
        variant="destructive"
      />
    </div>
  );
}
