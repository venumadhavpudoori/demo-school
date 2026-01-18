"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
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
interface UserResponse {
  id: number;
  email: string;
  profile_data: Record<string, string | null>;
  is_active: boolean;
}

interface TeacherResponse {
  id: number;
  employee_id: string;
  subjects: string[] | null;
  classes_assigned: number[] | null;
  qualifications: string | null;
  joining_date: string;
  status: string;
  user: UserResponse | null;
  created_at: string;
  updated_at: string;
}

// Form validation schema (no password required for edit)
const teacherEditFormSchema = z.object({
  employee_id: z
    .string()
    .min(1, "Employee ID is required")
    .max(50, "Employee ID must be 50 characters or less"),
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().optional(),
  phone: z.string().optional(),
  joining_date: z.string().min(1, "Joining date is required"),
  subjects: z.string().optional(),
  qualifications: z.string().max(1000, "Qualifications must be 1000 characters or less").optional(),
  status: z.enum(["active", "inactive", "on_leave"]),
});

type TeacherEditFormValues = z.infer<typeof teacherEditFormSchema>;

export default function EditTeacherPage() {
  const router = useRouter();
  const params = useParams();
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [teacher, setTeacher] = useState<TeacherResponse | null>(null);

  const teacherId = params.id as string;

  // Check permission
  const canEditTeacher = user?.role === "admin" || user?.role === "super_admin";

  const form = useForm<TeacherEditFormValues>({
    resolver: zodResolver(teacherEditFormSchema),
    defaultValues: {
      employee_id: "",
      first_name: "",
      last_name: "",
      phone: "",
      joining_date: "",
      subjects: "",
      qualifications: "",
      status: "active",
    },
  });

  // Fetch teacher data
  useEffect(() => {
    async function fetchTeacher() {
      if (!teacherId) return;

      setIsLoading(true);
      try {
        const response = await api.get<TeacherResponse>(`/api/teachers/${teacherId}`);
        setTeacher(response);

        // Populate form with existing data
        form.reset({
          employee_id: response.employee_id,
          first_name: response.user?.profile_data?.first_name || "",
          last_name: response.user?.profile_data?.last_name || "",
          phone: response.user?.profile_data?.phone || "",
          joining_date: response.joining_date?.split("T")[0] || "",
          subjects: response.subjects?.join(", ") || "",
          qualifications: response.qualifications || "",
          status: response.status as "active" | "inactive" | "on_leave",
        });
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch teacher");
        router.push("/dashboard/teachers");
      } finally {
        setIsLoading(false);
      }
    }
    fetchTeacher();
  }, [teacherId, form, router]);

  // Handle form submission
  const onSubmit = async (data: TeacherEditFormValues) => {
    if (!canEditTeacher) {
      toast.error("You don't have permission to edit teachers");
      return;
    }

    setIsSubmitting(true);
    try {
      // Parse subjects from comma-separated string
      const subjectsArray = data.subjects
        ? data.subjects.split(",").map((s) => s.trim()).filter((s) => s.length > 0)
        : null;

      const payload = {
        employee_id: data.employee_id,
        joining_date: data.joining_date,
        subjects: subjectsArray,
        qualifications: data.qualifications || null,
        status: data.status,
        profile_data: {
          first_name: data.first_name,
          last_name: data.last_name || null,
          phone: data.phone || null,
        },
      };

      await api.put(`/api/teachers/${teacherId}`, payload);
      toast.success("Teacher updated successfully");
      router.push(`/dashboard/teachers/${teacherId}`);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to update teacher");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!canEditTeacher) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">
              You don&apos;t have permission to edit teachers.
            </p>
            <Link href="/dashboard/teachers">
              <Button variant="link">Go back to teachers</Button>
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
          <div>
            <Skeleton className="h-8 w-48 mb-2" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-40" />
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-10 w-full" />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href={`/dashboard/teachers/${teacherId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Edit Teacher</h1>
          <p className="text-muted-foreground">
            Update teacher information
          </p>
        </div>
      </div>

      {/* Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Personal Information */}
          <Card>
            <CardHeader>
              <CardTitle>Personal Information</CardTitle>
              <CardDescription>
                Basic information about the teacher
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="first_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>First Name *</FormLabel>
                    <FormControl>
                      <Input placeholder="John" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="last_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Last Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Doe" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="phone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Phone</FormLabel>
                    <FormControl>
                      <Input placeholder="+1 234 567 8900" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="status"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Status *</FormLabel>
                    <FormControl>
                      <select
                        {...field}
                        className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                      >
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                        <option value="on_leave">On Leave</option>
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Employment Information */}
          <Card>
            <CardHeader>
              <CardTitle>Employment Information</CardTitle>
              <CardDescription>
                Employee details
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="employee_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Employee ID *</FormLabel>
                    <FormControl>
                      <Input placeholder="EMP-2024-001" {...field} />
                    </FormControl>
                    <FormDescription>
                      Unique identifier for the teacher
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="joining_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Joining Date *</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Professional Information */}
          <Card>
            <CardHeader>
              <CardTitle>Professional Information</CardTitle>
              <CardDescription>
                Teaching details and qualifications
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <FormField
                control={form.control}
                name="subjects"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Subjects</FormLabel>
                    <FormControl>
                      <Input placeholder="Math, Science, English" {...field} />
                    </FormControl>
                    <FormDescription>
                      Comma-separated list of subjects
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="qualifications"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Qualifications</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="B.Ed, M.Sc Mathematics, 5 years teaching experience..."
                        className="min-h-[100px]"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <Link href={`/dashboard/teachers/${teacherId}`}>
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
