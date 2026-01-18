"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Search,
  Plus,
  ChevronLeft,
  ChevronRight,
  Eye,
  Pencil,
  Trash2,
  Filter,
  X,
  Calendar,
  BookOpen,
  GraduationCap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/context/AuthContext";
import { useConfirmDialog } from "@/components/ConfirmDialog";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
interface ExamListItem {
  id: number;
  name: string;
  exam_type: string;
  class_id: number;
  class_name: string | null;
  start_date: string;
  end_date: string;
  academic_year: string;
}

interface ExamListResponse {
  items: ExamListItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
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

const examTypeLabels: Record<string, string> = {
  unit_test: "Unit Test",
  midterm: "Midterm",
  final: "Final",
  quarterly: "Quarterly",
  half_yearly: "Half Yearly",
  annual: "Annual",
};

const examTypeColors: Record<string, string> = {
  unit_test: "bg-blue-100 text-blue-800",
  midterm: "bg-purple-100 text-purple-800",
  final: "bg-green-100 text-green-800",
  quarterly: "bg-yellow-100 text-yellow-800",
  half_yearly: "bg-orange-100 text-orange-800",
  annual: "bg-red-100 text-red-800",
};

export default function ExamsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { confirm, ConfirmDialog } = useConfirmDialog();

  // State
  const [exams, setExams] = useState<ExamListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [teachers, setTeachers] = useState<TeacherItem[]>([]);
  const [isLoadingTeachers, setIsLoadingTeachers] = useState(true);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state from URL params
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");
  const classId = searchParams.get("class_id") || "";
  const examType = searchParams.get("exam_type") || "";
  const academicYear = searchParams.get("academic_year") || "";
  const teacherId = searchParams.get("teacher_id") || "";

  // Local filter state
  const [classFilter, setClassFilter] = useState(classId);
  const [examTypeFilter, setExamTypeFilter] = useState(examType);
  const [academicYearFilter, setAcademicYearFilter] = useState(academicYear);
  const [teacherFilter, setTeacherFilter] = useState(teacherId);

  // Check permissions
  const canManageExams = user?.role === "admin" || user?.role === "super_admin";

  // Update URL with filters
  const updateFilters = useCallback(
    (newFilters: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());
      Object.entries(newFilters).forEach(([key, value]) => {
        if (value) {
          params.set(key, value);
        } else {
          params.delete(key);
        }
      });
      if (!("page" in newFilters)) {
        params.set("page", "1");
      }
      router.push(`/dashboard/grades?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Fetch classes for filter dropdown
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

  // Fetch teachers for filter dropdown
  useEffect(() => {
    async function fetchTeachers() {
      setIsLoadingTeachers(true);
      try {
        const response = await api.get<TeacherListResponse>("/api/teachers", {
          page_size: 100,
          status: "active",
        });
        setTeachers(response?.items || []);
      } catch (err) {
        console.error("Failed to fetch teachers:", err);
        setTeachers([]);
      } finally {
        setIsLoadingTeachers(false);
      }
    }
    fetchTeachers();
  }, []);

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

  // Fetch exams
  useEffect(() => {
    async function fetchExams() {
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {
          page,
          page_size: pageSize,
        };
        if (classId) params.class_id = parseInt(classId);
        if (examType) params.exam_type = examType;
        if (academicYear) params.academic_year = academicYear;

        const response = await api.get<ExamListResponse>("/api/exams", params);
        setExams(response.items);
        setTotalCount(response.total_count);
        setTotalPages(response.total_pages);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch exams");
      } finally {
        setIsLoading(false);
      }
    }
    fetchExams();
  }, [page, pageSize, classId, examType, academicYear]);

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({
      class_id: classFilter,
      exam_type: examTypeFilter,
      academic_year: academicYearFilter,
      teacher_id: teacherFilter,
    });
    setShowFilters(false);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setClassFilter("");
    setExamTypeFilter("");
    setAcademicYearFilter("");
    setTeacherFilter("");
    router.push("/dashboard/grades");
  };

  // Handle delete exam
  const handleDelete = (exam: ExamListItem) => {
    confirm({
      title: "Delete Exam",
      description: `Are you sure you want to delete "${exam.name}"? This will also delete all associated grades.`,
      confirmLabel: "Delete",
      variant: "destructive",
      onConfirm: async () => {
        try {
          await api.delete(`/api/exams/${exam.id}`);
          toast.success("Exam deleted successfully");
          // Refresh the list
          const params: Record<string, string | number> = {
            page,
            page_size: pageSize,
          };
          if (classId) params.class_id = parseInt(classId);
          if (examType) params.exam_type = examType;
          if (academicYear) params.academic_year = academicYear;
          const response = await api.get<ExamListResponse>("/api/exams", params);
          setExams(response.items);
          setTotalCount(response.total_count);
          setTotalPages(response.total_pages);
        } catch (err) {
          const apiError = err as ApiError;
          toast.error(apiError.message || "Failed to delete exam");
        }
      },
    });
  };

  // Format date
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  // Check if any filters are active
  const hasActiveFilters = classId || examType || academicYear || teacherId;

  return (
    <div className="space-y-6">
      <ConfirmDialog />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Exams & Grades</h1>
          <p className="text-muted-foreground">
            Manage examinations and student grades
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/dashboard/grades/entry">
            <Button variant="outline">
              <GraduationCap className="h-4 w-4 mr-2" />
              Enter Grades
            </Button>
          </Link>
          <Link href="/dashboard/grades/analytics">
            <Button variant="outline">
              <BookOpen className="h-4 w-4 mr-2" />
              Analytics
            </Button>
          </Link>
          {canManageExams && (
            <Link href="/dashboard/grades/exams/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Exam
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                className={showFilters ? "bg-accent" : ""}
              >
                <Filter className="h-4 w-4 mr-2" />
                Filters
                {hasActiveFilters && (
                  <Badge variant="secondary" className="ml-2">
                    Active
                  </Badge>
                )}
              </Button>
              {hasActiveFilters && (
                <Button variant="ghost" onClick={handleClearFilters}>
                  <X className="h-4 w-4 mr-2" />
                  Clear
                </Button>
              )}
            </div>
          </div>

          {/* Filter Panel */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t">
              <div className="grid gap-4 md:grid-cols-5">
                <div>
                  <label className="text-sm font-medium mb-2 block">Class</label>
                  <select
                    value={classFilter}
                    onChange={(e) => setClassFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Classes</option>
                    {classes.map((cls) => (
                      <option key={cls.id} value={cls.id}>
                        {cls.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Teacher</label>
                  <select
                    value={teacherFilter}
                    onChange={(e) => setTeacherFilter(e.target.value)}
                    disabled={isLoadingTeachers}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm disabled:opacity-50"
                  >
                    <option value="">
                      {isLoadingTeachers ? "Loading teachers..." : "All Teachers"}
                    </option>
                    {teachers.map((teacher) => (
                      <option key={teacher.id} value={teacher.id}>
                        {getTeacherName(teacher)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Exam Type</label>
                  <select
                    value={examTypeFilter}
                    onChange={(e) => setExamTypeFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Types</option>
                    {Object.entries(examTypeLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Academic Year</label>
                  <Input
                    placeholder="e.g., 2024-2025"
                    value={academicYearFilter}
                    onChange={(e) => setAcademicYearFilter(e.target.value)}
                  />
                </div>
                <div className="flex items-end">
                  <Button onClick={handleApplyFilters} className="w-full">
                    Apply Filters
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Exams Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Exam List</span>
            <span className="text-sm font-normal text-muted-foreground">
              {totalCount} exam{totalCount !== 1 ? "s" : ""} found
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                  <Skeleton className="h-8 w-20" />
                </div>
              ))}
            </div>
          ) : exams.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No exams found</p>
              {hasActiveFilters && (
                <Button
                  variant="link"
                  onClick={handleClearFilters}
                  className="mt-2"
                >
                  Clear filters
                </Button>
              )}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Exam Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Class</TableHead>
                    <TableHead>Date Range</TableHead>
                    <TableHead>Academic Year</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {exams.map((exam) => (
                    <TableRow key={exam.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="p-2 bg-purple-100 rounded-lg">
                            <Calendar className="h-4 w-4 text-purple-600" />
                          </div>
                          <span className="font-medium">{exam.name}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={examTypeColors[exam.exam_type] || ""}
                        >
                          {examTypeLabels[exam.exam_type] || exam.exam_type}
                        </Badge>
                      </TableCell>
                      <TableCell>{exam.class_name || "-"}</TableCell>
                      <TableCell>
                        <div className="text-sm">
                          <p>{formatDate(exam.start_date)}</p>
                          <p className="text-muted-foreground">
                            to {formatDate(exam.end_date)}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>{exam.academic_year}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Link href={`/dashboard/grades/entry?exam_id=${exam.id}&class_id=${exam.class_id}`}>
                            <Button variant="ghost" size="icon-sm" title="Enter Grades">
                              <GraduationCap className="h-4 w-4" />
                            </Button>
                          </Link>
                          {canManageExams && (
                            <>
                              <Link href={`/dashboard/grades/exams/${exam.id}/edit`}>
                                <Button variant="ghost" size="icon-sm">
                                  <Pencil className="h-4 w-4" />
                                </Button>
                              </Link>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => handleDelete(exam)}
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => updateFilters({ page: String(page - 1) })}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => updateFilters({ page: String(page + 1) })}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
