"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, CreditCard, DollarSign, AlertCircle, CheckCircle } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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

interface PaymentResponse {
  fee_id: number;
  student_id: number;
  fee_type: string;
  total_amount: number;
  previous_paid: number;
  payment_amount: number;
  new_paid_amount: number;
  remaining_balance: number;
  previous_status: string;
  new_status: string;
  payment_date: string;
  payment_method: string | null;
  transaction_id: string | null;
}

// Payment methods
const PAYMENT_METHODS = [
  { value: "cash", label: "Cash" },
  { value: "card", label: "Credit/Debit Card" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "check", label: "Check" },
  { value: "online", label: "Online Payment" },
  { value: "other", label: "Other" },
];

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  partial: "bg-orange-100 text-orange-800",
  paid: "bg-green-100 text-green-800",
  overdue: "bg-red-100 text-red-800",
  waived: "bg-gray-100 text-gray-800",
};

// Form validation schema
const paymentFormSchema = z.object({
  amount: z.string().min(1, "Amount is required").refine(
    (val) => !isNaN(parseFloat(val)) && parseFloat(val) > 0,
    "Amount must be a positive number"
  ),
  payment_method: z.string().optional(),
  transaction_id: z.string().max(100, "Transaction ID must be 100 characters or less").optional(),
  payment_date: z.string().optional(),
});

type PaymentFormValues = z.infer<typeof paymentFormSchema>;

export default function PaymentPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const feeId = params.id as string;

  const [fee, setFee] = useState<FeeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [paymentResult, setPaymentResult] = useState<PaymentResponse | null>(null);

  // Check permission
  const canRecordPayment = user?.role === "admin" || user?.role === "super_admin";

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

  const form = useForm<PaymentFormValues>({
    resolver: zodResolver(paymentFormSchema),
    defaultValues: {
      amount: "",
      payment_method: "",
      transaction_id: "",
      payment_date: new Date().toISOString().split("T")[0],
    },
  });

  // Fetch fee details
  useEffect(() => {
    async function fetchFee() {
      setIsLoading(true);
      try {
        const response = await api.get<FeeResponse>(`/api/fees/${feeId}`);
        setFee(response);
        // Pre-fill with remaining amount
        form.setValue("amount", response.remaining.toString());
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch fee details");
        router.push("/dashboard/fees");
      } finally {
        setIsLoading(false);
      }
    }
    fetchFee();
  }, [feeId, router, form]);

  // Handle form submission
  const onSubmit = async (data: PaymentFormValues) => {
    if (!canRecordPayment) {
      toast.error("You don't have permission to record payments");
      return;
    }

    if (!fee) return;

    const paymentAmount = parseFloat(data.amount);
    if (paymentAmount > fee.remaining) {
      toast.error(`Payment amount cannot exceed remaining balance of ${formatCurrency(fee.remaining)}`);
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: Record<string, unknown> = {
        amount: paymentAmount,
      };
      
      if (data.payment_method) {
        payload.payment_method = data.payment_method;
      }
      if (data.transaction_id) {
        payload.transaction_id = data.transaction_id;
      }
      if (data.payment_date) {
        payload.payment_date = data.payment_date;
      }

      const response = await api.post<PaymentResponse>(`/api/fees/${feeId}/payment`, payload);
      setPaymentResult(response);
      toast.success("Payment recorded successfully");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to record payment");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Pay full amount
  const handlePayFullAmount = () => {
    if (fee) {
      form.setValue("amount", fee.remaining.toString());
    }
  };

  if (!canRecordPayment) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">
              You don&apos;t have permission to record payments.
            </p>
            <Link href="/dashboard/fees">
              <Button variant="link">Go back to fees</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

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

  // Show success screen after payment
  if (paymentResult) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/fees">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Payment Recorded</h1>
            <p className="text-muted-foreground">
              Payment has been successfully recorded
            </p>
          </div>
        </div>

        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-full">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="font-medium text-green-700">Payment Successful</p>
                <p className="text-sm text-green-600">
                  {formatCurrency(paymentResult.payment_amount)} has been recorded
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Payment Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-muted-foreground">Fee Type</p>
                  <p className="font-medium">{paymentResult.fee_type}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Amount</p>
                  <p className="font-medium">{formatCurrency(paymentResult.total_amount)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Payment Amount</p>
                  <p className="font-medium text-green-600">{formatCurrency(paymentResult.payment_amount)}</p>
                </div>
              </div>
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-muted-foreground">New Total Paid</p>
                  <p className="font-medium">{formatCurrency(paymentResult.new_paid_amount)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Remaining Balance</p>
                  <p className={`font-medium ${paymentResult.remaining_balance > 0 ? "text-orange-600" : "text-green-600"}`}>
                    {formatCurrency(paymentResult.remaining_balance)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary" className={statusColors[paymentResult.previous_status]}>
                      {paymentResult.previous_status}
                    </Badge>
                    <span className="text-muted-foreground">→</span>
                    <Badge variant="secondary" className={statusColors[paymentResult.new_status]}>
                      {paymentResult.new_status}
                    </Badge>
                  </div>
                </div>
              </div>
            </div>

            {(paymentResult.payment_method || paymentResult.transaction_id) && (
              <div className="mt-6 pt-4 border-t">
                <div className="grid gap-4 md:grid-cols-2">
                  {paymentResult.payment_method && (
                    <div>
                      <p className="text-sm text-muted-foreground">Payment Method</p>
                      <p className="font-medium capitalize">{paymentResult.payment_method.replace("_", " ")}</p>
                    </div>
                  )}
                  {paymentResult.transaction_id && (
                    <div>
                      <p className="text-sm text-muted-foreground">Transaction ID</p>
                      <p className="font-medium font-mono">{paymentResult.transaction_id}</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex justify-end gap-4">
          <Link href="/dashboard/fees">
            <Button variant="outline">Back to Fees</Button>
          </Link>
          <Link href={`/dashboard/fees/${feeId}`}>
            <Button>View Fee Details</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href={`/dashboard/fees/${feeId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Record Payment</h1>
          <p className="text-muted-foreground">
            {fee.fee_type} - {fee.student_name || `Student #${fee.student_id}`}
          </p>
        </div>
      </div>

      {/* Fee Summary */}
      <div className="grid gap-4 md:grid-cols-3">
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
                <p className="text-sm text-muted-foreground">Already Paid</p>
                <p className="text-xl font-bold text-green-600">{formatCurrency(fee.paid_amount)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-orange-200">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-orange-100 rounded-full">
                <AlertCircle className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Remaining</p>
                <p className="text-xl font-bold text-orange-600">{formatCurrency(fee.remaining)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Payment Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Payment Details</CardTitle>
              <CardDescription>
                Enter the payment information
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="amount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Payment Amount *</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                          $
                        </span>
                        <Input
                          type="number"
                          step="0.01"
                          min="0.01"
                          max={fee.remaining}
                          placeholder="0.00"
                          className="pl-7"
                          {...field}
                        />
                      </div>
                    </FormControl>
                    <FormDescription className="flex items-center justify-between">
                      <span>Maximum: {formatCurrency(fee.remaining)}</span>
                      <Button
                        type="button"
                        variant="link"
                        size="sm"
                        className="h-auto p-0"
                        onClick={handlePayFullAmount}
                      >
                        Pay full amount
                      </Button>
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="payment_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Payment Date</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormDescription>
                      Defaults to today if not specified
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="payment_method"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Payment Method</FormLabel>
                    <FormControl>
                      <select
                        {...field}
                        className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                      >
                        <option value="">Select payment method</option>
                        {PAYMENT_METHODS.map((method) => (
                          <option key={method.value} value={method.value}>
                            {method.label}
                          </option>
                        ))}
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="transaction_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Transaction ID</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., TXN-123456" {...field} />
                    </FormControl>
                    <FormDescription>
                      Reference number for the payment
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <Link href={`/dashboard/fees/${feeId}`}>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </Link>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Recording..." : "Record Payment"}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
