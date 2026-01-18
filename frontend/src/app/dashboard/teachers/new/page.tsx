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
const teacherFormSchema = z.object({
  employee_id: z
    .string()
    .min(1, "Employee ID is required")
    .max(50, "Employee ID must be 50 characters or less"),
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().optional(),
  phone: z.string().optional(),
  joining_date: z.string().min(1, "Joining date is required"),
  subjects: z.string().optional(),
  qualifications: z.string().max(1000, "Qualifications must be 1000 characters or less").optional(),
});

type TeacherFormValues = z.infer<typeof teacherFormSchema>;

export default function NewTeacherPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Check permission
  const canCreateTeacher = user?.role === "admin" || user?.role === "super_admin";

  const form = useForm<TeacherFormValues>({
    resolver: zodResolver(teacherFormSchema),
    defaultValues: {
      employee_id: "",
      email: "",
      password: "",
      first_name: "",
      last_name: "",
      phone: "",
      joining_date: new Date().toISOString().split("T")[0],
      subjects: "",
      qualifications: "",
    },
  });

  // Handle form submission
  const onSubmit = async (data: TeacherFormValues) => {
    if (!canCreateTeacher) {
      toast.error("You don't have permission to create teachers");
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
        email: data.email,
        password: data.password,
        joining_date: data.joining_date,
        subjects: subjectsArray,
        classes_assigned: null,
        qualifications: data.qualifications || null,
        profile_data: {
          first_name: data.first_name,
          last_name: data.last_name || null,
          phone: data.phone || null,
        },
      };

      await api.post("/api/teachers", payload);
      toast.success("Teacher created successfully");
      router.push("/dashboard/teachers");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to create teacher");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!canCreateTeacher) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">
              You don&apos;t have permission to create teachers.
            </p>
            <Link href="/dashboard/teachers">
              <Button variant="link">Go back to teachers</Button>
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
        <Link href="/dashboard/teachers">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Add New Teacher</h1>
          <p className="text-muted-foreground">
            Create a new teacher record
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
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email *</FormLabel>
                    <FormControl>
                      <Input type="email" placeholder="john.doe@example.com" {...field} />
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
            </CardContent>
          </Card>

          {/* Account Information */}
          <Card>
            <CardHeader>
              <CardTitle>Account Information</CardTitle>
              <CardDescription>
                Login credentials for the teacher
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
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password *</FormLabel>
                    <FormControl>
                      <Input type="password" placeholder="••••••••" {...field} />
                    </FormControl>
                    <FormDescription>
                      Minimum 8 characters
                    </FormDescription>
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
            <CardContent className="grid gap-4 md:grid-cols-2">
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
                  <FormItem className="md:col-span-2">
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
            <Link href="/dashboard/teachers">
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </Link>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create Teacher"}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
