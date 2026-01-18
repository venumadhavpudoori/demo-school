"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

// Common fee types
const FEE_TYPES = [
  "Tuition Fee",
  "Admission Fee",
  "Examination Fee",
  "Library Fee",
  "Laboratory Fee",
  "Sports Fee",
  "Transportation Fee",
  "Hostel Fee",
  "Uniform Fee",
  "Books Fee",
  "Activity Fee",
  "Other",
];

// Form validation schema
const feeFormSchema = z.object({
  student_id: z.string().min(1, "Student is required"),
  fee_type: z.string().min(1, "Fee type is required").max(100, "Fee type must be 100 characters or less"),
  custom_fee_type: z.string().max(100, "Custom fee type must be 100 characters or less").optional(),
  amount: z.string().min(1, "Amount is required").refine(
    (val) => !isNaN(parseFloat(val)) && parseFloat(val) > 0,
    "Amount must be a positive number"
  ),
  due_date: z.string().min(1, "Due date is required"),
  academic_year: z.string().min(1, "Academic year is required").max(20, "Academic year must be 20 characters or less"),
});

type FeeFormValues = z.infer<typeof feeFormSchema>;

export default function NewFeePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [isLoadingStudents, setIsLoadingStudents] = useState(true);

  // Check permission
  const canCreateFee = user?.role === "admin" || user?.role === "super_admin";

  // Get current academic year
  const getCurrentAcademicYear = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    // Academic year typically starts in August/September
    if (month >= 7) {
      return `${year}-${year + 1}`;
    }
    return `${year - 1}-${year}`;
  };

  const form = useForm<FeeFormValues>({
    resolver: zodResolver(feeFormSchema),
    defaultValues: {
      student_id: "",
      fee_type: "",
      custom_fee_type: "",
      amount: "",
      due_date: "",
      academic_year: getCurrentAcademicYear(),
    },
  });

  const selectedFeeType = form.watch("fee_type");

  // Fetch students
  useEffect(() => {
    async function fetchStudents() {
      setIsLoadingStudents(true);
      try {
        const response = await api.get<StudentListResponse>("/api/students", {
          page_size: 100,
        });
        setStudents(response.items);
      } catch (err) {
        console.error("Failed to fetch students:", err);
        toast.error("Failed to load students");
      } finally {
        setIsLoadingStudents(false);
      }
    }
    fetchStudents();
  }, []);

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

  // Handle form submission
  const onSubmit = async (data: FeeFormValues) => {
    if (!canCreateFee) {
      toast.error("You don't have permission to create fees");
      return;
    }

    setIsSubmitting(true);
    try {
      // Determine the actual fee type
      const feeType = data.fee_type === "Other" && data.custom_fee_type 
        ? data.custom_fee_type 
        : data.fee_type;

      const payload = {
        student_id: parseInt(data.student_id),
        fee_type: feeType,
        amount: parseFloat(data.amount),
        due_date: data.due_date,
        academic_year: data.academic_year,
      };

      await api.post("/api/fees", payload);
      toast.success("Fee created successfully");
      router.push("/dashboard/fees");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to create fee");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!canCreateFee) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">
              You don&apos;t have permission to create fees.
            </p>
            <Link href="/dashboard/fees">
              <Button variant="link">Go back to fees</Button>
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
        <Link href="/dashboard/fees">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Create New Fee</h1>
          <p className="text-muted-foreground">
            Add a new fee record for a student
          </p>
        </div>
      </div>

      {/* Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Student Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Student Information</CardTitle>
              <CardDescription>
                Select the student for this fee
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="student_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Student *</FormLabel>
                    <FormControl>
                      <select
                        {...field}
                        disabled={isLoadingStudents}
                        className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm disabled:opacity-50"
                      >
                        <option value="">
                          {isLoadingStudents ? "Loading students..." : "Select a student"}
                        </option>
                        {students.map((student) => (
                          <option key={student.id} value={student.id}>
                            {getStudentName(student)} ({student.admission_number})
                          </option>
                        ))}
                      </select>
                    </FormControl>
                    <FormDescription>
                      Select the student who will be charged this fee
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Fee Details */}
          <Card>
            <CardHeader>
              <CardTitle>Fee Details</CardTitle>
              <CardDescription>
                Enter the fee information
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="fee_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fee Type *</FormLabel>
                    <FormControl>
                      <select
                        {...field}
                        className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                      >
                        <option value="">Select fee type</option>
                        {FEE_TYPES.map((type) => (
                          <option key={type} value={type}>
                            {type}
                          </option>
                        ))}
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {selectedFeeType === "Other" && (
                <FormField
                  control={form.control}
                  name="custom_fee_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Custom Fee Type *</FormLabel>
                      <FormControl>
                        <Input placeholder="Enter custom fee type" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              <FormField
                control={form.control}
                name="amount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Amount *</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                          $
                        </span>
                        <Input
                          type="number"
                          step="0.01"
                          min="0.01"
                          placeholder="0.00"
                          className="pl-7"
                          {...field}
                        />
                      </div>
                    </FormControl>
                    <FormDescription>
                      Enter the fee amount in dollars
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="due_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Due Date *</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormDescription>
                      The date by which the fee should be paid
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="academic_year"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Academic Year *</FormLabel>
                    <FormControl>
                      <Input placeholder="2024-2025" {...field} />
                    </FormControl>
                    <FormDescription>
                      Format: YYYY-YYYY (e.g., 2024-2025)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <Link href="/dashboard/fees">
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </Link>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create Fee"}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
