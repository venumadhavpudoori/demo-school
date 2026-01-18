"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
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

// Form validation schema
const leaveRequestFormSchema = z.object({
  from_date: z.string().min(1, "Start date is required"),
  to_date: z.string().min(1, "End date is required"),
  reason: z.string().min(1, "Reason is required").max(1000, "Reason must be 1000 characters or less"),
}).refine((data) => {
  const from = new Date(data.from_date);
  const to = new Date(data.to_date);
  return to >= from;
}, {
  message: "End date must be on or after start date",
  path: ["to_date"],
});

type LeaveRequestFormValues = z.infer<typeof leaveRequestFormSchema>;

export default function EditLeaveRequestPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const leaveRequestId = params.id as string;

  const [leaveRequest, setLeaveRequest] = useState<LeaveRequestResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<LeaveRequestFormValues>({
    resolver: zodResolver(leaveRequestFormSchema),
    defaultValues: {
      from_date: "",
      to_date: "",
      reason: "",
    },
  });

  // Check permission
  const canEdit = () => {
    if (!leaveRequest) return false;
    if (leaveRequest.status !== "pending") return false;
    return leaveRequest.requester_id === user?.id;
  };

  // Fetch leave request
  useEffect(() => {
    async function fetchLeaveRequest() {
      setIsLoading(true);
      try {
        const response = await api.get<LeaveRequestResponse>(`/api/leave-requests/${leaveRequestId}`);
        setLeaveRequest(response);
        form.reset({
          from_date: response.from_date,
          to_date: response.to_date,
          reason: response.reason,
        });
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch leave request");
        router.push("/leave-requests");
      } finally {
        setIsLoading(false);
      }
    }
    fetchLeaveRequest();
  }, [leaveRequestId, router, form]);

  // Handle form submission
  const onSubmit = async (data: LeaveRequestFormValues) => {
    if (!canEdit()) {
      toast.error("You don't have permission to edit this leave request");
      return;
    }

    setIsSubmitting(true);
    try {
      await api.put(`/api/leave-requests/${leaveRequestId}`, data);
      toast.success("Leave request updated successfully");
      router.push(`/leave-requests/${leaveRequestId}`);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to update leave request");
    } finally {
      setIsSubmitting(false);
    }
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
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!leaveRequest) {
    return null;
  }

  if (!canEdit()) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">
              {leaveRequest.status !== "pending"
                ? "Only pending leave requests can be edited."
                : "You don't have permission to edit this leave request."}
            </p>
            <Link href={`/leave-requests/${leaveRequestId}`}>
              <Button variant="link">Go back to leave request</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href={`/leave-requests/${leaveRequestId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Edit Leave Request</h1>
          <p className="text-muted-foreground">
            Update your leave request details
          </p>
        </div>
      </div>

      {/* Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Leave Request Details */}
          <Card>
            <CardHeader>
              <CardTitle>Leave Request Details</CardTitle>
              <CardDescription>
                Update the details for your leave request
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="from_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>From Date *</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormDescription>
                        Start date of your leave
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="to_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>To Date *</FormLabel>
                      <FormControl>
                        <Input 
                          type="date" 
                          min={form.watch("from_date")}
                          {...field} 
                        />
                      </FormControl>
                      <FormDescription>
                        End date of your leave
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="reason"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Reason *</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Please provide a reason for your leave request"
                        className="min-h-[150px]"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Explain why you need this leave (max 1000 characters)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <Link href={`/leave-requests/${leaveRequestId}`}>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </Link>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
