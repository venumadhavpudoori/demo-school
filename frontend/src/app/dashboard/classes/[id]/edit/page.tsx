"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { useForm, useFieldArray } from "react-hook-form";
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
  FormDescription,
} from "@/components/ui/form";
import { useAuth } from "@/context/AuthContext";
import { useConfirmDialog } from "@/components/ConfirmDialog";
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

interface ClassResponse {
  id: number;
  name: string;
  grade_level: number;
  academic_year: string;
  class_teacher_id: number | null;
}

interface SectionResponse {
  id: number;
  class_id: number;
  name: string;
  capacity: number;
  students_count: number;
}

// Form validation schema
const sectionSchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, "Section name is required").max(50, "Section name must be 50 characters or less"),
  capacity: z.number().min(1, "Capacity must be at least 1").max(100, "Capacity must be 100 or less"),
  students_count: z.number().optional(),
  isNew: z.boolean().optional(),
  isDeleted: z.boolean().optional(),
});

const classFormSchema = z.object({
  name: z.string().min(1, "Class name is required").max(100, "Class name must be 100 characters or less"),
  grade_level: z.number().min(1, "Grade level must be at least 1").max(12, "Grade level must be 12 or less"),
  academic_year: z.string().min(4, "Academic year is required").max(20, "Academic year must be 20 characters or less"),
  class_teacher_id: z.string().optional(),
  sections: z.array(sectionSchema).optional(),
});

type ClassFormValues = z.infer<typeof classFormSchema>;


export default function EditClassPage() {
  const router = useRouter();
  const params = useParams();
  const classId = params.id as string;
  const { user } = useAuth();
  const { confirm, ConfirmDialog } = useConfirmDialog();
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [teachers, setTeachers] = useState<TeacherItem[]>([]);
  const [originalSections, setOriginalSections] = useState<SectionResponse[]>([]);

  // Check permission
  const canEditClass = user?.role === "admin" || user?.role === "super_admin";

  const form = useForm<ClassFormValues>({
    resolver: zodResolver(classFormSchema),
    defaultValues: {
      name: "",
      grade_level: 1,
      academic_year: "",
      class_teacher_id: "",
      sections: [],
    },
  });

  const { fields, append, remove, update } = useFieldArray({
    control: form.control,
    name: "sections",
  });

  // Fetch class data and teachers
  useEffect(() => {
    async function fetchData() {
      setIsLoading(true);
      try {
        // Fetch class data
        const classData = await api.get<ClassResponse>(`/api/classes/${classId}`);
        
        // Fetch sections for this class
        const sectionsData = await api.get<SectionResponse[]>(`/api/classes/${classId}/sections`);
        setOriginalSections(sectionsData);

        // Fetch teachers
        const teachersResponse = await api.get<TeacherListResponse>("/api/teachers", {
          page_size: 100,
          status: "active",
        });
        setTeachers(teachersResponse.items);

        // Set form values
        form.reset({
          name: classData.name,
          grade_level: classData.grade_level,
          academic_year: classData.academic_year,
          class_teacher_id: classData.class_teacher_id?.toString() || "",
          sections: sectionsData.map((s) => ({
            id: s.id,
            name: s.name,
            capacity: s.capacity,
            students_count: s.students_count,
            isNew: false,
            isDeleted: false,
          })),
        });
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch class data");
        router.push("/dashboard/classes");
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [classId, form, router]);

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
    if (!canEditClass) {
      toast.error("You don't have permission to edit classes");
      return;
    }

    setIsSubmitting(true);
    try {
      // Update the class
      const classPayload = {
        name: data.name,
        grade_level: data.grade_level,
        academic_year: data.academic_year,
        class_teacher_id: data.class_teacher_id ? parseInt(data.class_teacher_id) : null,
      };

      await api.put(`/api/classes/${classId}`, classPayload);

      // Handle sections
      if (data.sections) {
        for (const section of data.sections) {
          if (section.isDeleted && section.id) {
            // Delete existing section
            await api.delete(`/api/sections/${section.id}`);
          } else if (section.isNew) {
            // Create new section
            await api.post(`/api/classes/${classId}/sections`, {
              class_id: parseInt(classId),
              name: section.name,
              capacity: section.capacity,
            });
          } else if (section.id) {
            // Update existing section
            const original = originalSections.find((s) => s.id === section.id);
            if (original && (original.name !== section.name || original.capacity !== section.capacity)) {
              await api.put(`/api/sections/${section.id}`, {
                name: section.name,
                capacity: section.capacity,
              });
            }
          }
        }
      }

      toast.success("Class updated successfully");
      router.push("/dashboard/classes");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to update class");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Add a new section
  const addSection = () => {
    const existingNames = fields.filter((f) => !f.isDeleted).map((f) => f.name);
    let nextLetter = "A";
    for (let i = 0; i < 26; i++) {
      const letter = String.fromCharCode(65 + i);
      if (!existingNames.includes(letter)) {
        nextLetter = letter;
        break;
      }
    }
    append({ name: nextLetter, capacity: 40, isNew: true, isDeleted: false });
  };

  // Mark section for deletion
  const markSectionForDeletion = (index: number) => {
    const section = fields[index];
    if (section.students_count && section.students_count > 0) {
      toast.error("Cannot delete section with enrolled students");
      return;
    }
    
    if (section.isNew) {
      // If it's a new section, just remove it
      remove(index);
    } else {
      // Mark existing section for deletion
      confirm({
        title: "Delete Section",
        description: `Are you sure you want to delete section "${section.name}"? This action will be applied when you save the class.`,
        confirmLabel: "Delete",
        variant: "destructive",
        onConfirm: () => {
          update(index, { ...section, isDeleted: true });
        },
      });
    }
  };

  // Restore a deleted section
  const restoreSection = (index: number) => {
    const section = fields[index];
    update(index, { ...section, isDeleted: false });
  };


  if (!canEditClass) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">
              You don&apos;t have permission to edit classes.
            </p>
            <Link href="/dashboard/classes">
              <Button variant="link">Go back to classes</Button>
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
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-9 w-full" />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ConfirmDialog />

      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard/classes">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Edit Class</h1>
          <p className="text-muted-foreground">
            Update class information and sections
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
                      <Input type="number" min={1} max={12} {...field} />
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
                        className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                      >
                        <option value="">Select class teacher</option>
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
                    Manage sections for this class
                  </CardDescription>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={addSection}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Section
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {fields.filter((f) => !f.isDeleted).length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No sections in this class.</p>
                  <p className="text-sm">Click &quot;Add Section&quot; to create sections for this class.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {fields.map((field, index) => {
                    if (field.isDeleted) return null;
                    return (
                      <div key={field.id} className="flex items-end gap-4 p-4 border rounded-lg">
                        <FormField
                          control={form.control}
                          name={`sections.${index}.name`}
                          render={({ field: inputField }) => (
                            <FormItem className="flex-1">
                              <FormLabel>Section Name *</FormLabel>
                              <FormControl>
                                <Input placeholder="e.g., A" {...inputField} />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name={`sections.${index}.capacity`}
                          render={({ field: inputField }) => (
                            <FormItem className="flex-1">
                              <FormLabel>Capacity *</FormLabel>
                              <FormControl>
                                <Input type="number" min={1} max={100} {...inputField} />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <div className="flex-1">
                          <FormLabel>Students</FormLabel>
                          <div className="h-9 flex items-center text-sm text-muted-foreground">
                            {field.students_count || 0} enrolled
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => markSectionForDeletion(index)}
                          className="text-destructive hover:text-destructive"
                          disabled={Boolean(field.students_count && field.students_count > 0)}
                          title={field.students_count && field.students_count > 0 ? "Cannot delete section with enrolled students" : "Delete section"}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Show deleted sections that can be restored */}
              {fields.some((f) => f.isDeleted) && (
                <div className="mt-4 pt-4 border-t">
                  <p className="text-sm text-muted-foreground mb-2">Sections marked for deletion:</p>
                  <div className="space-y-2">
                    {fields.map((field, index) => {
                      if (!field.isDeleted) return null;
                      return (
                        <div key={field.id} className="flex items-center justify-between p-2 bg-destructive/10 rounded">
                          <span className="text-sm line-through">Section {field.name}</span>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => restoreSection(index)}
                          >
                            Restore
                          </Button>
                        </div>
                      );
                    })}
                  </div>
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
              {isSubmitting ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
