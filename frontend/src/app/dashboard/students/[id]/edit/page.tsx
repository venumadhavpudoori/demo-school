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
import { Skeleton } from "@/components/ui/skeleton";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
interface UserResponse {
  id: number;
  email: string;
  profile_data: Record<string, unknown>;
  is_active: boolean;
}

interface StudentResponse {
  id: number;
  admission_number: string;
  class_id: number | null;
  section_id: number | null;
  roll_number: number | null;
  date_of_birth: string;
  gender: string;
  address: string | null;
  admission_date: string;
  status: string;
  user: UserResponse | null;
  created_at: string;
  updated_at: string;
}

interface ClassItem {
  id: number;
  name: string;
  grade_level: number;
  academic_year: string;
}

interface ClassListResponse {
  items: ClassItem[];
  total_count: number;
}

interface SectionItem {
  id: number;
  class_id: number;
  name: string;
}

interface SectionListResponse {
  items: SectionItem[];
  total_count: number;
}

// Form validation schema
const studentEditSchema = z.object({
  admission_number: z
    .string()
    .min(1, "Admission number is required")
    .max(50, "Admission number must be 50 characters or less"),
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().optional(),
  phone: z.string().optional(),
  class_id: z.string().optional(),
  section_id: z.string().optional(),
  roll_number: z.string().optional(),
  address: z.string().max(500, "Address must be 500 characters or less").optional(),
  status: z.enum(["active", "inactive", "graduated", "transferred"]),
});

type StudentEditValues = z.infer<typeof studentEditSchema>;

export default function EditStudentPage() {
  const router = useRouter();
  const params = useParams();
  const studentId = params.id as string;
  const { user } = useAuth();
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [student, setStudent] = useState<StudentResponse | null>(null);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [sections, setSections] = useState<SectionItem[]>([]);

  // Check permission
  const canEditStudent = user?.role === "admin" || user?.role === "super_admin" || user?.role === "teacher";

  const form = useForm<StudentEditValues>({
    resolver: zodResolver(studentEditSchema),
    defaultValues: {
      admission_number: "",
      first_name: "",
      last_name: "",
      phone: "",
      class_id: "",
      section_id: "",
      roll_number: "",
      address: "",
      status: "active",
    },
  });

  const selectedClassId = form.watch("class_id");

  // Fetch student data
  useEffect(() => {
    async function fetchStudent() {
      try {
        const response = await api.get<StudentResponse>(`/api/students/${studentId}`);
        setStudent(response);
        
        // Set form values
        form.reset({
          admission_number: response.admission_number,
          first_name: (response.user?.profile_data?.first_name as string) || "",
          last_name: (response.user?.profile_data?.last_name as string) || "",
          phone: (response.user?.profile_data?.phone as string) || "",
          class_id: response.class_id?.toString() || "",
          section_id: response.section_id?.toString() || "",
          roll_number: response.roll_number?.toString() || "",
          address: response.address || "",
          status: response.status as "active" | "inactive" | "graduated" | "transferred",
        });
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch student");
        router.push("/dashboard/students");
      } finally {
        setIsLoading(false);
      }
    }
    fetchStudent();
  }, [studentId, form, router]);

  // Fetch classes
  useEffect(() => {
    async function fetchClasses() {
      try {
        const response = await api.get<ClassListResponse>("/api/classes", {
          page_size: 100,
        });
        setClasses(response.items);
      } catch (err) {
        console.error("Failed to fetch classes:", err);
      }
    }
    fetchClasses();
  }, []);

  // Fetch sections when class changes
  useEffect(() => {
    async function fetchSections() {
      if (!selectedClassId) {
        setSections([]);
        return;
      }
      try {
        const response = await api.get<SectionListResponse>("/api/sections", {
          class_id: parseInt(selectedClassId),
          page_size: 100,
        });
        setSections(response.items);
      } catch (err) {
        console.error("Failed to fetch sections:", err);
      }
    }
    fetchSections();
  }, [selectedClassId]);

  // Handle form submission
  const onSubmit = async (data: StudentEditValues) => {
    if (!canEditStudent) {
      toast.error("You don't have permission to edit students");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        admission_number: data.admission_number,
        class_id: data.class_id ? parseInt(data.class_id) : null,
        section_id: data.section_id ? parseInt(data.section_id) : null,
        roll_number: data.roll_number ? parseInt(data.roll_number) : null,
        address: data.address || null,
        status: data.status,
        profile_data: {
          first_name: data.first_name,
          last_name: data.last_name || null,
          phone: data.phone || null,
        },
      };

      await api.put(`/api/students/${studentId}`, payload);
      toast.success("Student updated successfully");
      router.push(`/dashboard/students/${studentId}`);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to update student");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!canEditStudent) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">
              You don&apos;t have permission to edit students.
            </p>
            <Link href="/dashboard/students">
              <Button variant="link">Go back to students</Button>
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
          <CardHeader>
            <Skeleton className="h-6 w-40" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href={`/dashboard/students/${studentId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Edit Student</h1>
          <p className="text-muted-foreground">
            Update student information for {student?.user?.email || student?.admission_number}
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
                Basic information about the student
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
                name="address"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Address</FormLabel>
                    <FormControl>
                      <Input placeholder="123 Main St, City, Country" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Academic Information */}
          <Card>
            <CardHeader>
              <CardTitle>Academic Information</CardTitle>
              <CardDescription>
                Class and enrollment details
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="admission_number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Admission Number *</FormLabel>
                    <FormControl>
                      <Input placeholder="STU-2024-001" {...field} />
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
                        className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                      >
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                        <option value="graduated">Graduated</option>
                        <option value="transferred">Transferred</option>
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="class_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Class</FormLabel>
                    <FormControl>
                      <select
                        {...field}
                        className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                      >
                        <option value="">Select class</option>
                        {classes.map((cls) => (
                          <option key={cls.id} value={cls.id}>
                            {cls.name}
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
                name="section_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Section</FormLabel>
                    <FormControl>
                      <select
                        {...field}
                        disabled={!selectedClassId}
                        className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm disabled:opacity-50"
                      >
                        <option value="">Select section</option>
                        {sections.map((section) => (
                          <option key={section.id} value={section.id}>
                            {section.name}
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
                name="roll_number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Roll Number</FormLabel>
                    <FormControl>
                      <Input type="number" min="1" placeholder="1" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <Link href={`/dashboard/students/${studentId}`}>
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
