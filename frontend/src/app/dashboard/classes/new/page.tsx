"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { useForm, useFieldArray } from "react-hook-form";
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
interface TeacherItem {
  id: number;
  employee_id: string;
  user: {
    email: string;
    profile_data: Record<string, unknown>;
  } | null;
}

interface TeacherListResponse {
  items: TeacherItem[];
  total_count: number;
}

// Form validation schema
const sectionSchema = z.object({
  name: z.string().min(1, "Section name is required").max(50, "Section name must be 50 characters or less"),
  capacity: z.number().min(1, "Capacity must be at least 1").max(100, "Capacity must be 100 or less"),
});

const classFormSchema = z.object({
  name: z.string().min(1, "Class name is required").max(100, "Class name must be 100 characters or less"),
  grade_level: z.number().min(1, "Grade level must be at least 1").max(12, "Grade level must be 12 or less"),
  academic_year: z.string().min(4, "Academic year is required").max(20, "Academic year must be 20 characters or less"),
  class_teacher_id: z.string().optional(),
  sections: z.array(sectionSchema).optional(),
});

type ClassFormValues = z.infer<typeof classFormSchema>;

export default function NewClassPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [teachers, setTeachers] = useState<TeacherItem[]>([]);
  const [isLoadingTeachers, setIsLoadingTeachers] = useState(true);

  // Check permission
  const canCreateClass = user?.role === "admin" || user?.role === "super_admin";

  const form = useForm<ClassFormValues>({
    resolver: zodResolver(classFormSchema),
    defaultValues: {
      name: "",
      grade_level: 1,
      academic_year: `${new Date().getFullYear()}-${new Date().getFullYear() + 1}`,
      class_teacher_id: "",
      sections: [],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "sections",
  });

  // Fetch teachers
  useEffect(() => {
    async function fetchTeachers() {
      if (!canCreateClass) {
        setIsLoadingTeachers(false);
        return;
      }
      setIsLoadingTeachers(true);
      try {
        const response = await api.get<TeacherListResponse>("/api/teachers", {
          page_size: 100,
          status: "active",
        });
        setTeachers(response?.items || []);
      } catch (err) {
        const apiError = err as ApiError;
        console.error("Failed to fetch teachers:", apiError);
        toast.error(apiError.message || "Failed to load teachers");
        setTeachers([]);
      } finally {
        setIsLoadingTeachers(false);
      }
    }
    fetchTeachers();
  }, [canCreateClass]);

  // Get teacher display name
  const getTeacherName = (teacher: TeacherItem) => {
    if (teacher.user?.profile_data) {
      const firstName = teacher.user.profile_data.first_name as string;
      const lastName = teacher.user.profile_data.last_name as string;
      if (firstName || lastName) {
        return `${firstName || ""} ${lastName || ""}`.trim();
      }
    }
    return teacher.user?.email || teacher.employee_id;
  };

  // Handle form submission
  const onSubmit = async (data: ClassFormValues) => {
    if (!canCreateClass) {
      toast.error("You don't have permission to create classes");
      return;
    }

    setIsSubmitting(true);
    try {
      // Create the class first
      const classPayload = {
        name: data.name,
        grade_level: data.grade_level,
        academic_year: data.academic_year,
        class_teacher_id: data.class_teacher_id ? parseInt(data.class_teacher_id) : null,
      };

      const createdClass = await api.post<{ id: number }>("/api/classes", classPayload);

      // Create sections if any
      if (data.sections && data.sections.length > 0) {
        for (const section of data.sections) {
          await api.post(`/api/classes/${createdClass.id}/sections`, {
            class_id: createdClass.id,
            name: section.name,
            capacity: section.capacity,
          });
        }
      }

      toast.success("Class created successfully");
      router.push("/dashboard/classes");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to create class");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Add a new section
  const addSection = () => {
    const nextLetter = String.fromCharCode(65 + fields.length); // A, B, C, ...
    append({ name: nextLetter, capacity: 40 });
  };

  if (!canCreateClass) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">
              You don&apos;t have permission to create classes.
            </p>
            <Link href="/dashboard/classes">
              <Button variant="link">Go back to classes</Button>
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
        <Link href="/dashboard/classes">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Add New Class</h1>
          <p className="text-muted-foreground">
            Create a new class with sections
          </p>
        </div>
      </div>

      {/* Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Class Information */}
          <Card>
            <CardHeader>
              <CardTitle>Class Information</CardTitle>
              <CardDescription>
                Basic information about the class
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Class Name *</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., Class 10" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="grade_level"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Grade Level *</FormLabel>
                    <FormControl>
                      <Input 
                        type="number" 
                        min={1} 
                        max={12} 
                        {...field}
                        onChange={(e) => field.onChange(parseInt(e.target.value) || 1)}
                      />
                    </FormControl>
                    <FormDescription>
                      Grade level from 1 to 12
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
                      <Input placeholder="e.g., 2024-2025" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="class_teacher_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Class Teacher</FormLabel>
                    <FormControl>
                      <select
                        {...field}
                        disabled={isLoadingTeachers}
                        className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm disabled:opacity-50"
                      >
                        <option value="">
                          {isLoadingTeachers ? "Loading teachers..." : "Select class teacher"}
                        </option>
                        {teachers.map((teacher) => (
                          <option key={teacher.id} value={teacher.id}>
                            {getTeacherName(teacher)} ({teacher.employee_id})
                          </option>
                        ))}
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Sections */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Sections</CardTitle>
                  <CardDescription>
                    Add sections to this class (optional)
                  </CardDescription>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={addSection}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Section
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {fields.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No sections added yet.</p>
                  <p className="text-sm">Click &quot;Add Section&quot; to create sections for this class.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {fields.map((field, index) => (
                    <div key={field.id} className="flex items-end gap-4 p-4 border rounded-lg">
                      <FormField
                        control={form.control}
                        name={`sections.${index}.name`}
                        render={({ field }) => (
                          <FormItem className="flex-1">
                            <FormLabel>Section Name *</FormLabel>
                            <FormControl>
                              <Input placeholder="e.g., A" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name={`sections.${index}.capacity`}
                        render={({ field }) => (
                          <FormItem className="flex-1">
                            <FormLabel>Capacity *</FormLabel>
                            <FormControl>
                              <Input 
                                type="number" 
                                min={1} 
                                max={100} 
                                {...field}
                                onChange={(e) => field.onChange(parseInt(e.target.value) || 1)}
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => remove(index)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <Link href="/dashboard/classes">
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </Link>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create Class"}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
