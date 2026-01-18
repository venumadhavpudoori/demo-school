"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, CreditCard, DollarSign, Calendar, User, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
interface FeeResponse {
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

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  partial: "bg-orange-100 text-orange-800",
  paid: "bg-green-100 text-green-800",
  overdue: "bg-red-100 text-red-800",
  waived: "bg-gray-100 text-gray-800",
};

export default function FeeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const feeId = params.id as string;

  const [fee, setFee] = useState<FeeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check if user can manage fees
  const canManageFees = user?.role === "admin" || user?.role === "super_admin";

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
      month: "long",
      day: "numeric",
    });
  };

  // Check if fee is overdue
  const isOverdue = (fee: FeeResponse) => {
    if (fee.status === "paid" || fee.status === "waived") return false;
    return new Date(fee.due_date) < new Date();
  };

  // Fetch fee details
  useEffect(() => {
    async function fetchFee() {
      setIsLoading(true);
      try {
        const response = await api.get<FeeResponse>(`/api/fees/${feeId}`);
        setFee(response);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch fee details");
        router.push("/dashboard/fees");
      } finally {
        setIsLoading(false);
      }
    }
    fetchFee();
  }, [feeId, router]);

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
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!fee) {
    return null;
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
            <h1 className="text-2xl font-bold">Fee Details</h1>
            <p className="text-muted-foreground">
              {fee.fee_type} - {fee.academic_year}
            </p>
          </div>
        </div>
        {canManageFees && fee.status !== "paid" && fee.status !== "waived" && (
          <Link href={`/dashboard/fees/${fee.id}/payment`}>
            <Button>
              <CreditCard className="h-4 w-4 mr-2" />
              Record Payment
            </Button>
          </Link>
        )}
      </div>

      {/* Status Alert */}
      {isOverdue(fee) && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-red-100 rounded-full">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <p className="font-medium text-red-700">This fee is overdue</p>
                <p className="text-sm text-red-600">
                  The due date was {formatDate(fee.due_date)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Fee Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-full">
                <DollarSign className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Amount</p>
                <p className="text-xl font-bold">{formatCurrency(fee.amount)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-full">
                <CreditCard className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Paid Amount</p>
                <p className="text-xl font-bold text-green-600">{formatCurrency(fee.paid_amount)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-orange-100 rounded-full">
                <DollarSign className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Remaining</p>
                <p className="text-xl font-bold text-orange-600">{formatCurrency(fee.remaining)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gray-100 rounded-full">
                <Calendar className="h-5 w-5 text-gray-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Due Date</p>
                <p className={`text-lg font-medium ${isOverdue(fee) ? "text-red-600" : ""}`}>
                  {formatDate(fee.due_date)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Fee Details */}
      <Card>
        <CardHeader>
          <CardTitle>Fee Information</CardTitle>
          <CardDescription>
            Detailed information about this fee record
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Student</p>
                <div className="flex items-center gap-2 mt-1">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <p className="font-medium">{fee.student_name || `Student #${fee.student_id}`}</p>
                </div>
              </div>

              <div>
                <p className="text-sm text-muted-foreground">Fee Type</p>
                <p className="font-medium mt-1">{fee.fee_type}</p>
              </div>

              <div>
                <p className="text-sm text-muted-foreground">Academic Year</p>
                <p className="font-medium mt-1">{fee.academic_year}</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <Badge
                  variant="secondary"
                  className={`${statusColors[fee.status] || ""} mt-1`}
                >
                  {fee.status}
                </Badge>
              </div>

              <div>
                <p className="text-sm text-muted-foreground">Due Date</p>
                <p className={`font-medium mt-1 ${isOverdue(fee) ? "text-red-600" : ""}`}>
                  {formatDate(fee.due_date)}
                </p>
              </div>

              {fee.payment_date && (
                <div>
                  <p className="text-sm text-muted-foreground">Last Payment Date</p>
                  <p className="font-medium mt-1">{formatDate(fee.payment_date)}</p>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-end gap-4">
        <Link href="/dashboard/fees">
          <Button variant="outline">Back to Fees</Button>
        </Link>
        {canManageFees && fee.status !== "paid" && fee.status !== "waived" && (
          <Link href={`/dashboard/fees/${fee.id}/payment`}>
            <Button>
              <CreditCard className="h-4 w-4 mr-2" />
              Record Payment
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}
