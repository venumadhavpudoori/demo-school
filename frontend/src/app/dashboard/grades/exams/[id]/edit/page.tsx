"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Save, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

interface ExamResponse {
  id: number;
  name: string;
  exam_type: string;
  class_id: number;
  class_name: string | null;
  start_date: string;
  end_date: string;
  academic_year: string;
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

const examTypes = [
  { value: "unit_test", label: "Unit Test" },
  { value: "midterm", label: "Midterm" },
  { value: "final", label: "Final" },
  { value: "quarterly", label: "Quarterly" },
  { value: "half_yearly", label: "Half Yearly" },
  { value: "annual", label: "Annual" },
];

export default function EditExamPage() {
  const router = useRouter();
  const params = useParams();
  const examId = params.id as string;
  const { user } = useAuth();

  // Form state
  const [name, setName] = useState("");
  const [examType, setExamType] = useState("unit_test");
  const [classId, setClassId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [academicYear, setAcademicYear] = useState("");

  // UI state
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingClasses, setIsLoadingClasses] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Check permissions
  const canManageExams = user?.role === "admin" || user?.role === "super_admin";

  // Redirect if no permission
  useEffect(() => {
    if (user && !canManageExams) {
      router.push("/grades");
    }
  }, [user, canManageExams, router]);

  // Fetch exam data
  useEffect(() => {
    async function fetchExam() {
      try {
        const exam = await api.get<ExamResponse>(`/api/exams/${examId}`);
        setName(exam.name);
        setExamType(exam.exam_type);
        setClassId(String(exam.class_id));
        setStartDate(exam.start_date);
        setEndDate(exam.end_date);
        setAcademicYear(exam.academic_year);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch exam");
        router.push("/grades");
      } finally {
        setIsLoading(false);
      }
    }
    fetchExam();
  }, [examId, router]);

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
      } finally {
        setIsLoadingClasses(false);
      }
    }
    fetchClasses();
  }, []);

  // Validate form
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!name.trim()) {
      newErrors.name = "Exam name is required";
    }
    if (!startDate) {
      newErrors.startDate = "Start date is required";
    }
    if (!endDate) {
      newErrors.endDate = "End date is required";
    }
    if (startDate && endDate && new Date(endDate) < new Date(startDate)) {
      newErrors.endDate = "End date must be on or after start date";
    }
    if (!academicYear.trim()) {
      newErrors.academicYear = "Academic year is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSaving(true);
    try {
      await api.put(`/api/exams/${examId}`, {
        name: name.trim(),
        exam_type: examType,
        start_date: startDate,
        end_date: endDate,
        academic_year: academicYear.trim(),
      });

      toast.success("Exam updated successfully");
      router.push("/grades");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to update exam");
    } finally {
      setIsSaving(false);
    }
  };

  if (!canManageExams) {
    return null;
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
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-9 w-full" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/grades">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Edit Exam</h1>
          <p className="text-muted-foreground">
            Update examination details
          </p>
        </div>
      </div>

      {/* Form */}
      <Card>
        <CardHeader>
          <CardTitle>Exam Details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              {/* Exam Name */}
              <div className="space-y-2">
                <Label htmlFor="name">Exam Name *</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., First Unit Test"
                  className={errors.name ? "border-destructive" : ""}
                />
                {errors.name && (
                  <p className="text-sm text-destructive">{errors.name}</p>
                )}
              </div>

              {/* Exam Type */}
              <div className="space-y-2">
                <Label htmlFor="examType">Exam Type *</Label>
                <select
                  id="examType"
                  value={examType}
                  onChange={(e) => setExamType(e.target.value)}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                >
                  {examTypes.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Class (Read-only) */}
              <div className="space-y-2">
                <Label htmlFor="classId">Class</Label>
                {isLoadingClasses ? (
                  <Skeleton className="h-9 w-full" />
                ) : (
                  <select
                    id="classId"
                    value={classId}
                    disabled
                    className="w-full h-9 rounded-md border border-input bg-muted px-3 py-1 text-sm opacity-70"
                  >
                    <option value="">Select Class</option>
                    {classes.map((cls) => (
                      <option key={cls.id} value={cls.id}>
                        {cls.name} ({cls.academic_year})
                      </option>
                    ))}
                  </select>
                )}
                <p className="text-xs text-muted-foreground">
                  Class cannot be changed after creation
                </p>
              </div>

              {/* Academic Year */}
              <div className="space-y-2">
                <Label htmlFor="academicYear">Academic Year *</Label>
                <Input
                  id="academicYear"
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                  placeholder="e.g., 2024-2025"
                  className={errors.academicYear ? "border-destructive" : ""}
                />
                {errors.academicYear && (
                  <p className="text-sm text-destructive">{errors.academicYear}</p>
                )}
              </div>

              {/* Start Date */}
              <div className="space-y-2">
                <Label htmlFor="startDate">Start Date *</Label>
                <Input
                  id="startDate"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className={errors.startDate ? "border-destructive" : ""}
                />
                {errors.startDate && (
                  <p className="text-sm text-destructive">{errors.startDate}</p>
                )}
              </div>

              {/* End Date */}
              <div className="space-y-2">
                <Label htmlFor="endDate">End Date *</Label>
                <Input
                  id="endDate"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className={errors.endDate ? "border-destructive" : ""}
                />
                {errors.endDate && (
                  <p className="text-sm text-destructive">{errors.endDate}</p>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-4 pt-4 border-t">
              <Link href="/grades">
                <Button type="button" variant="outline">
                  Cancel
                </Button>
              </Link>
              <Button type="submit" disabled={isSaving}>
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
