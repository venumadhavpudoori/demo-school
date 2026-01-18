"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Save, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

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

export default function NewExamPage() {
  const router = useRouter();
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
  const [isLoadingClasses, setIsLoadingClasses] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Check permissions
  const canManageExams = user?.role === "admin" || user?.role === "super_admin";

  // Redirect if no permission
  useEffect(() => {
    if (user && !canManageExams) {
      router.push("/dashboard/grades");
    }
  }, [user, canManageExams, router]);

  // Fetch classes
  useEffect(() => {
    async function fetchClasses() {
      try {
        const response = await api.get<ClassListResponse>("/api/classes", {
          page_size: 100,
        });
        setClasses(response.items);
        // Set default academic year from first class if available
        if (response.items.length > 0 && !academicYear) {
          setAcademicYear(response.items[0].academic_year);
        }
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
    if (!classId) {
      newErrors.classId = "Class is required";
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
      await api.post("/api/exams", {
        name: name.trim(),
        exam_type: examType,
        class_id: parseInt(classId),
        start_date: startDate,
        end_date: endDate,
        academic_year: academicYear.trim(),
      });

      toast.success("Exam created successfully");
      router.push("/dashboard/grades");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to create exam");
    } finally {
      setIsSaving(false);
    }
  };

  if (!canManageExams) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard/grades">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Create New Exam</h1>
          <p className="text-muted-foreground">
            Add a new examination to the system
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

              {/* Class */}
              <div className="space-y-2">
                <Label htmlFor="classId">Class *</Label>
                {isLoadingClasses ? (
                  <div className="h-9 flex items-center">
                    <Loader2 className="h-4 w-4 animate-spin" />
                  </div>
                ) : (
                  <select
                    id="classId"
                    value={classId}
                    onChange={(e) => setClassId(e.target.value)}
                    className={`w-full h-9 rounded-md border bg-background px-3 py-1 text-sm ${
                      errors.classId ? "border-destructive" : "border-input"
                    }`}
                  >
                    <option value="">Select Class</option>
                    {classes.map((cls) => (
                      <option key={cls.id} value={cls.id}>
                        {cls.name} ({cls.academic_year})
                      </option>
                    ))}
                  </select>
                )}
                {errors.classId && (
                  <p className="text-sm text-destructive">{errors.classId}</p>
                )}
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
              <Link href="/dashboard/grades">
                <Button type="button" variant="outline">
                  Cancel
                </Button>
              </Link>
              <Button type="submit" disabled={isSaving}>
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Create Exam
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
