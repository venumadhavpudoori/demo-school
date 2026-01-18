"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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

// Form validation schema
const leaveRequestFormSchema = z.object({
  requester_type: z.enum(["teacher", "student"]),
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

export default function NewLeaveRequestPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Determine requester type based on user role
  const getDefaultRequesterType = (): "teacher" | "student" => {
    if (user?.role === "teacher") return "teacher";
    if (user?.role === "student") return "student";
    return "teacher"; // Default for admin
  };

  // Check permission
  const canCreateLeaveRequest = user?.role === "teacher" || user?.role === "student" || 
    user?.role === "admin" || user?.role === "super_admin";

  // Get today's date in YYYY-MM-DD format
  const getTodayDate = () => {
    const today = new Date();
    return today.toISOString().split("T")[0];
  };

  const form = useForm<LeaveRequestFormValues>({
    resolver: zodResolver(leaveRequestFormSchema),
    defaultValues: {
      requester_type: getDefaultRequesterType(),
      from_date: "",
      to_date: "",
      reason: "",
    },
  });

  // Handle form submission
  const onSubmit = async (data: LeaveRequestFormValues) => {
    if (!canCreateLeaveRequest) {
      toast.error("You don't have permission to create leave requests");
      return;
    }

    setIsSubmitting(true);
    try {
      await api.post("/api/leave-requests", data);
      toast.success("Leave request submitted successfully");
      router.push("/dashboard/leave-requests");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to submit leave request");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!canCreateLeaveRequest) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">
              You don&apos;t have permission to create leave requests.
            </p>
            <Link href="/dashboard/leave-requests">
              <Button variant="link">Go back to leave requests</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Determine if user can select requester type (only admins can)
  const canSelectRequesterType = user?.role === "admin" || user?.role === "super_admin";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard/leave-requests">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">New Leave Request</h1>
          <p className="text-muted-foreground">
            Submit a new leave request
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
                Enter the details for your leave request
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {canSelectRequesterType && (
                <FormField
                  control={form.control}
                  name="requester_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Requester Type *</FormLabel>
                      <FormControl>
                        <select
                          {...field}
                          className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                        >
                          <option value="teacher">Teacher</option>
                          <option value="student">Student</option>
                        </select>
                      </FormControl>
                      <FormDescription>
                        Select the type of requester
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="from_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>From Date *</FormLabel>
                      <FormControl>
                        <Input 
                          type="date" 
                          min={getTodayDate()}
                          {...field} 
                        />
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
                          min={form.watch("from_date") || getTodayDate()}
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
            <Link href="/dashboard/leave-requests">
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </Link>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Submitting..." : "Submit Request"}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
