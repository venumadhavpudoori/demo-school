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
interface UserResponse {
  id: number;
  email: string;
  profile_data: Record<string, unknown>;
  is_active: boolean;
}

interface StudentListItem {
  id: number;
  admission_number: string;
  class_id: number | null;
  section_id: number | null;
  roll_number: number | null;
  date_of_birth: string;
  gender: string;
  status: string;
  user: UserResponse | null;
}

interface StudentListResponse {
  items: StudentListItem[];
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

interface SectionItem {
  id: number;
  class_id: number;
  name: string;
}

interface SectionListResponse {
  items: SectionItem[];
  total_count: number;
}

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-gray-100 text-gray-800",
  graduated: "bg-blue-100 text-blue-800",
  transferred: "bg-yellow-100 text-yellow-800",
  deleted: "bg-red-100 text-red-800",
};

export default function StudentsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { confirm, ConfirmDialog } = useConfirmDialog();

  // State
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [sections, setSections] = useState<SectionItem[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state from URL params
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");
  const search = searchParams.get("search") || "";
  const classId = searchParams.get("class_id") || "";
  const sectionId = searchParams.get("section_id") || "";
  const status = searchParams.get("status") || "";

  // Local filter state for inputs
  const [searchInput, setSearchInput] = useState(search);
  const [classFilter, setClassFilter] = useState(classId);
  const [sectionFilter, setSectionFilter] = useState(sectionId);
  const [statusFilter, setStatusFilter] = useState(status);

  // Check if user can manage students
  const canManageStudents = user?.role === "admin" || user?.role === "super_admin";
  const canEditStudents = canManageStudents || user?.role === "teacher";

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
      // Reset to page 1 when filters change (except when changing page)
      if (!("page" in newFilters)) {
        params.set("page", "1");
      }
      router.push(`/dashboard/students?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Fetch classes for filter dropdown
  useEffect(() => {
    async function fetchClasses() {
      if (!user) return;
      try {
        const response = await api.get<ClassListResponse>("/api/classes", {
          page_size: 100,
        });
        setClasses(response?.items || []);
      } catch (err) {
        console.error("Failed to fetch classes:", err);
        setClasses([]);
      }
    }
    fetchClasses();
  }, [user]);

  // Fetch sections when class changes
  useEffect(() => {
    async function fetchSections() {
      if (!user || !classFilter) {
        setSections([]);
        return;
      }
      try {
        const response = await api.get<SectionListResponse>("/api/sections", {
          class_id: parseInt(classFilter),
          page_size: 100,
        });
        setSections(response?.items || []);
      } catch (err) {
        console.error("Failed to fetch sections:", err);
        setSections([]);
      }
    }
    fetchSections();
  }, [user, classFilter]);

  // Fetch students
  useEffect(() => {
    async function fetchStudents() {
      if (!user) return;
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {
          page,
          page_size: pageSize,
        };
        if (search) params.search = search;
        if (classId) params.class_id = parseInt(classId);
        if (sectionId) params.section_id = parseInt(sectionId);
        if (status) params.status = status;

        const response = await api.get<StudentListResponse>("/api/students", params);
        setStudents(response?.items || []);
        setTotalCount(response?.total_count || 0);
        setTotalPages(response?.total_pages || 0);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch students");
        setStudents([]);
        setTotalCount(0);
        setTotalPages(0);
      } finally {
        setIsLoading(false);
      }
    }
    fetchStudents();
  }, [user, page, pageSize, search, classId, sectionId, status]);

  // Handle search submit
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilters({ search: searchInput });
  };

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({
      class_id: classFilter,
      section_id: sectionFilter,
      status: statusFilter,
    });
    setShowFilters(false);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setSearchInput("");
    setClassFilter("");
    setSectionFilter("");
    setStatusFilter("");
    router.push("/dashboard/students");
  };

  // Handle delete student
  const handleDelete = (student: StudentListItem) => {
    const studentName =
      student.user?.profile_data?.first_name ||
      student.user?.email ||
      student.admission_number;

    confirm({
      title: "Delete Student",
      description: `Are you sure you want to delete ${studentName}? This action will soft-delete the student record.`,
      confirmLabel: "Delete",
      variant: "destructive",
      onConfirm: async () => {
        try {
          await api.delete(`/api/students/${student.id}`);
          toast.success("Student deleted successfully");
          // Refresh the list
          const params: Record<string, string | number> = {
            page,
            page_size: pageSize,
          };
          if (search) params.search = search;
          if (classId) params.class_id = parseInt(classId);
          if (sectionId) params.section_id = parseInt(sectionId);
          if (status) params.status = status;
          const response = await api.get<StudentListResponse>("/api/students", params);
          setStudents(response?.items || []);
          setTotalCount(response?.total_count || 0);
          setTotalPages(response?.total_pages || 0);
        } catch (err) {
          const apiError = err as ApiError;
          toast.error(apiError.message || "Failed to delete student");
        }
      },
    });
  };

  // Get student display name
  const getStudentName = (student: StudentListItem) => {
    if (student.user?.profile_data) {
      const firstName = student.user.profile_data.first_name as string;
      const lastName = student.user.profile_data.last_name as string;
      if (firstName || lastName) {
        return `${firstName || ""} ${lastName || ""}`.trim();
      }
    }
    return student.user?.email || student.admission_number;
  };

  // Get class name by ID
  const getClassName = (classId: number | null) => {
    if (!classId) return "-";
    const cls = classes.find((c) => c.id === classId);
    return cls?.name || "-";
  };

  // Check if any filters are active
  const hasActiveFilters = search || classId || sectionId || status;

  return (
    <div className="space-y-6">
      <ConfirmDialog />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Students</h1>
          <p className="text-muted-foreground">
            Manage student records and information
          </p>
        </div>
        {canManageStudents && (
          <Link href="/dashboard/students/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Student
            </Button>
          </Link>
        )}
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            {/* Search */}
            <form onSubmit={handleSearch} className="flex gap-2 flex-1 max-w-md">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name, email, or admission number..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>

            {/* Filter Toggle */}
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
              <div className="grid gap-4 md:grid-cols-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">Class</label>
                  <select
                    value={classFilter}
                    onChange={(e) => {
                      setClassFilter(e.target.value);
                      setSectionFilter("");
                    }}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Classes</option>
                    {(classes || []).map((cls) => (
                      <option key={cls.id} value={cls.id}>
                        {cls.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Section</label>
                  <select
                    value={sectionFilter}
                    onChange={(e) => setSectionFilter(e.target.value)}
                    disabled={!classFilter}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm disabled:opacity-50"
                  >
                    <option value="">All Sections</option>
                    {(sections || []).map((section) => (
                      <option key={section.id} value={section.id}>
                        {section.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Status</label>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Statuses</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                    <option value="graduated">Graduated</option>
                    <option value="transferred">Transferred</option>
                  </select>
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

      {/* Students Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Student List</span>
            <span className="text-sm font-normal text-muted-foreground">
              {totalCount} student{totalCount !== 1 ? "s" : ""} found
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
          ) : !students || students.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No students found</p>
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
                    <TableHead>Name</TableHead>
                    <TableHead>Admission No.</TableHead>
                    <TableHead>Class</TableHead>
                    <TableHead>Roll No.</TableHead>
                    <TableHead>Gender</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(students || []).map((student) => (
                    <TableRow key={student.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{getStudentName(student)}</p>
                          <p className="text-sm text-muted-foreground">
                            {student.user?.email}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>{student.admission_number}</TableCell>
                      <TableCell>{getClassName(student.class_id)}</TableCell>
                      <TableCell>{student.roll_number || "-"}</TableCell>
                      <TableCell className="capitalize">{student.gender || "-"}</TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={statusColors[student.status] || ""}
                        >
                          {student.status || "unknown"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Link href={`/dashboard/students/${student.id}`}>
                            <Button variant="ghost" size="icon-sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                          {canEditStudents && (
                            <Link href={`/dashboard/students/${student.id}/edit`}>
                              <Button variant="ghost" size="icon-sm">
                                <Pencil className="h-4 w-4" />
                              </Button>
                            </Link>
                          )}
                          {canManageStudents && (
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => handleDelete(student)}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
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
