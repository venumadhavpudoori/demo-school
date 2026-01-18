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
  Users,
  BookOpen,
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
interface TeacherInfo {
  id: number;
  employee_id: string;
  user: {
    email: string;
    profile_data: Record<string, unknown>;
  } | null;
}

interface ClassListItem {
  id: number;
  name: string;
  grade_level: number;
  academic_year: string;
  class_teacher_id: number | null;
  class_teacher: TeacherInfo | null;
  created_at: string | null;
  updated_at: string | null;
}

interface ClassListResponse {
  items: ClassListItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

interface SectionSummary {
  id: number;
  name: string;
  capacity: number;
  students_count: number;
}

export default function ClassesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { confirm, ConfirmDialog } = useConfirmDialog();

  // State
  const [classes, setClasses] = useState<ClassListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const [sectionCounts, setSectionCounts] = useState<Record<number, number>>({});

  // Filter state from URL params
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");
  const search = searchParams.get("search") || "";
  const academicYear = searchParams.get("academic_year") || "";

  // Local filter state for inputs
  const [searchInput, setSearchInput] = useState(search);
  const [academicYearFilter, setAcademicYearFilter] = useState(academicYear);

  // Check if user can manage classes
  const canManageClasses = user?.role === "admin" || user?.role === "super_admin";

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
      router.push(`/dashboard/classes?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Fetch classes
  useEffect(() => {
    async function fetchClasses() {
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {
          page,
          page_size: pageSize,
        };
        if (academicYear) params.academic_year = academicYear;

        const response = await api.get<ClassListResponse>("/api/classes", params);
        setClasses(response.items);
        setTotalCount(response.total_count);
        setTotalPages(response.total_pages);

        // Fetch section counts for each class
        const counts: Record<number, number> = {};
        for (const cls of response.items) {
          try {
            const sections = await api.get<SectionSummary[]>(`/api/classes/${cls.id}/sections`);
            counts[cls.id] = sections.length;
          } catch {
            counts[cls.id] = 0;
          }
        }
        setSectionCounts(counts);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch classes");
      } finally {
        setIsLoading(false);
      }
    }
    fetchClasses();
  }, [page, pageSize, academicYear]);

  // Handle search submit
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilters({ search: searchInput });
  };

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({
      academic_year: academicYearFilter,
    });
    setShowFilters(false);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setSearchInput("");
    setAcademicYearFilter("");
    router.push("/dashboard/classes");
  };

  // Handle delete class
  const handleDelete = (cls: ClassListItem) => {
    confirm({
      title: "Delete Class",
      description: `Are you sure you want to delete "${cls.name}"? This action cannot be undone.`,
      confirmLabel: "Delete",
      variant: "destructive",
      onConfirm: async () => {
        try {
          await api.delete(`/api/classes/${cls.id}`);
          toast.success("Class deleted successfully");
          // Refresh the list
          const params: Record<string, string | number> = {
            page,
            page_size: pageSize,
          };
          if (academicYear) params.academic_year = academicYear;
          const response = await api.get<ClassListResponse>("/api/classes", params);
          setClasses(response.items);
          setTotalCount(response.total_count);
          setTotalPages(response.total_pages);
        } catch (err) {
          const apiError = err as ApiError;
          toast.error(apiError.message || "Failed to delete class");
        }
      },
    });
  };

  // Get teacher display name
  const getTeacherName = (teacher: TeacherInfo | null) => {
    if (!teacher) return "Not assigned";
    if (teacher.user?.profile_data) {
      const firstName = teacher.user.profile_data.first_name as string;
      const lastName = teacher.user.profile_data.last_name as string;
      if (firstName || lastName) {
        return `${firstName || ""} ${lastName || ""}`.trim();
      }
    }
    return teacher.user?.email || teacher.employee_id;
  };

  // Check if any filters are active
  const hasActiveFilters = search || academicYear;

  // Filter classes by search (client-side since API doesn't support search)
  const filteredClasses = search
    ? classes.filter(
        (cls) =>
          cls.name.toLowerCase().includes(search.toLowerCase()) ||
          cls.academic_year.toLowerCase().includes(search.toLowerCase())
      )
    : classes;

  return (
    <div className="space-y-6">
      <ConfirmDialog />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Classes</h1>
          <p className="text-muted-foreground">
            Manage classes and sections
          </p>
        </div>
        {canManageClasses && (
          <Link href="/dashboard/classes/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Class
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
                  placeholder="Search by class name..."
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

      {/* Classes Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Class List</span>
            <span className="text-sm font-normal text-muted-foreground">
              {totalCount} class{totalCount !== 1 ? "es" : ""} found
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
          ) : filteredClasses.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No classes found</p>
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
                    <TableHead>Class Name</TableHead>
                    <TableHead>Grade Level</TableHead>
                    <TableHead>Academic Year</TableHead>
                    <TableHead>Class Teacher</TableHead>
                    <TableHead>Sections</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredClasses.map((cls) => (
                    <TableRow key={cls.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="p-2 bg-blue-100 rounded-lg">
                            <BookOpen className="h-4 w-4 text-blue-600" />
                          </div>
                          <span className="font-medium">{cls.name}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">Grade {cls.grade_level}</Badge>
                      </TableCell>
                      <TableCell>{cls.academic_year}</TableCell>
                      <TableCell>{getTeacherName(cls.class_teacher)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Users className="h-4 w-4 text-muted-foreground" />
                          <span>{sectionCounts[cls.id] ?? 0}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Link href={`/dashboard/classes/${cls.id}`}>
                            <Button variant="ghost" size="icon-sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                          {canManageClasses && (
                            <>
                              <Link href={`/dashboard/classes/${cls.id}/edit`}>
                                <Button variant="ghost" size="icon-sm">
                                  <Pencil className="h-4 w-4" />
                                </Button>
                              </Link>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => handleDelete(cls)}
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
