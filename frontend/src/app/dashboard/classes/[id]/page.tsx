"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Pencil,
  Trash2,
  Users,
  BookOpen,
  GraduationCap,
  ChevronLeft,
  ChevronRight,
  Search,
  Eye,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

interface ClassResponse {
  id: number;
  name: string;
  grade_level: number;
  academic_year: string;
  class_teacher_id: number | null;
  class_teacher: TeacherInfo | null;
  created_at: string | null;
  updated_at: string | null;
}

interface SectionSummary {
  id: number;
  name: string;
  capacity: number;
  students_count: number;
}

interface SubjectSummary {
  id: number;
  name: string;
  code: string;
  credits: number;
  teacher_id: number | null;
  teacher: TeacherInfo | null;
}

interface StudentUserInfo {
  id: number;
  email: string;
  profile_data: Record<string, unknown>;
}

interface EnrolledStudent {
  id: number;
  admission_number: string;
  class_id: number | null;
  section_id: number | null;
  roll_number: number | null;
  date_of_birth: string;
  gender: string;
  status: string;
  user: StudentUserInfo | null;
}

interface EnrolledStudentsResponse {
  items: EnrolledStudent[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}


const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-gray-100 text-gray-800",
  graduated: "bg-blue-100 text-blue-800",
  transferred: "bg-yellow-100 text-yellow-800",
  deleted: "bg-red-100 text-red-800",
};

export default function ClassDetailPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const classId = params.id as string;
  const { user } = useAuth();
  const { confirm, ConfirmDialog } = useConfirmDialog();

  const [isLoading, setIsLoading] = useState(true);
  const [classData, setClassData] = useState<ClassResponse | null>(null);
  const [sections, setSections] = useState<SectionSummary[]>([]);
  const [subjects, setSubjects] = useState<SubjectSummary[]>([]);
  const [students, setStudents] = useState<EnrolledStudent[]>([]);
  const [studentsLoading, setStudentsLoading] = useState(false);
  const [totalStudents, setTotalStudents] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  // Pagination and filter state
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");
  const sectionFilter = searchParams.get("section_id") || "";
  const [searchInput, setSearchInput] = useState("");

  // Check permissions
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
      router.push(`/dashboard/classes/${classId}?${params.toString()}`);
    },
    [router, searchParams, classId]
  );

  // Fetch class data
  useEffect(() => {
    async function fetchClassData() {
      setIsLoading(true);
      try {
        const [classResponse, sectionsResponse, subjectsResponse] = await Promise.all([
          api.get<ClassResponse>(`/api/classes/${classId}`),
          api.get<SectionSummary[]>(`/api/classes/${classId}/sections`),
          api.get<SubjectSummary[]>(`/api/classes/${classId}/subjects`),
        ]);
        setClassData(classResponse);
        setSections(sectionsResponse);
        setSubjects(subjectsResponse);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch class data");
        router.push("/dashboard/classes");
      } finally {
        setIsLoading(false);
      }
    }
    fetchClassData();
  }, [classId, router]);

  // Fetch students
  useEffect(() => {
    async function fetchStudents() {
      setStudentsLoading(true);
      try {
        const params: Record<string, string | number> = {
          page,
          page_size: pageSize,
        };
        if (sectionFilter) {
          params.section_id = parseInt(sectionFilter);
        }
        const response = await api.get<EnrolledStudentsResponse>(
          `/api/classes/${classId}/students`,
          params
        );
        setStudents(response.items);
        setTotalStudents(response.total_count);
        setTotalPages(response.total_pages);
      } catch (err) {
        console.error("Failed to fetch students:", err);
      } finally {
        setStudentsLoading(false);
      }
    }
    if (!isLoading) {
      fetchStudents();
    }
  }, [classId, page, pageSize, sectionFilter, isLoading]);

  // Handle delete
  const handleDelete = () => {
    if (!classData) return;

    confirm({
      title: "Delete Class",
      description: `Are you sure you want to delete "${classData.name}"? This action cannot be undone.`,
      confirmLabel: "Delete",
      variant: "destructive",
      onConfirm: async () => {
        try {
          await api.delete(`/api/classes/${classId}`);
          toast.success("Class deleted successfully");
          router.push("/dashboard/classes");
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

  // Get student display name
  const getStudentName = (student: EnrolledStudent) => {
    if (student.user?.profile_data) {
      const firstName = student.user.profile_data.first_name as string;
      const lastName = student.user.profile_data.last_name as string;
      if (firstName || lastName) {
        return `${firstName || ""} ${lastName || ""}`.trim();
      }
    }
    return student.user?.email || student.admission_number;
  };

  // Get section name by ID
  const getSectionName = (sectionId: number | null) => {
    if (!sectionId) return "-";
    const section = sections.find((s) => s.id === sectionId);
    return section?.name || "-";
  };

  // Filter students by search (client-side)
  const filteredStudents = searchInput
    ? students.filter((student) => {
        const name = getStudentName(student).toLowerCase();
        const admissionNumber = student.admission_number.toLowerCase();
        const search = searchInput.toLowerCase();
        return name.includes(search) || admissionNumber.includes(search);
      })
    : students;

  // Calculate total students across all sections
  const totalEnrolledStudents = sections.reduce((sum, s) => sum + s.students_count, 0);
  const totalCapacity = sections.reduce((sum, s) => sum + s.capacity, 0);


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
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!classData) {
    return null;
  }

  return (
    <div className="space-y-6">
      <ConfirmDialog />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/classes">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{classData.name}</h1>
              <Badge variant="outline">Grade {classData.grade_level}</Badge>
            </div>
            <p className="text-muted-foreground">
              Academic Year: {classData.academic_year}
            </p>
          </div>
        </div>
        {canManageClasses && (
          <div className="flex gap-2">
            <Link href={`/dashboard/classes/${classId}/edit`}>
              <Button variant="outline">
                <Pencil className="h-4 w-4 mr-2" />
                Edit
              </Button>
            </Link>
            <Button variant="destructive" onClick={handleDelete}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        )}
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Users className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Students</p>
                <p className="text-2xl font-bold">{totalEnrolledStudents}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-green-100 rounded-lg">
                <BookOpen className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Sections</p>
                <p className="text-2xl font-bold">{sections.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-purple-100 rounded-lg">
                <GraduationCap className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Subjects</p>
                <p className="text-2xl font-bold">{subjects.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Users className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Capacity</p>
                <p className="text-2xl font-bold">
                  {totalEnrolledStudents}/{totalCapacity}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="students" className="space-y-4">
        <TabsList>
          <TabsTrigger value="students">Students</TabsTrigger>
          <TabsTrigger value="sections">Sections</TabsTrigger>
          <TabsTrigger value="subjects">Subjects</TabsTrigger>
          <TabsTrigger value="info">Information</TabsTrigger>
        </TabsList>


        {/* Students Tab */}
        <TabsContent value="students" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <CardTitle>Enrolled Students</CardTitle>
                  <CardDescription>
                    {totalStudents} student{totalStudents !== 1 ? "s" : ""} enrolled in this class
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search students..."
                      value={searchInput}
                      onChange={(e) => setSearchInput(e.target.value)}
                      className="pl-9 w-64"
                    />
                  </div>
                  <select
                    value={sectionFilter}
                    onChange={(e) => updateFilters({ section_id: e.target.value })}
                    className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Sections</option>
                    {sections.map((section) => (
                      <option key={section.id} value={section.id}>
                        Section {section.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {studentsLoading ? (
                <div className="space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <Skeleton className="h-10 w-10 rounded-full" />
                      <div className="space-y-2 flex-1">
                        <Skeleton className="h-4 w-48" />
                        <Skeleton className="h-3 w-32" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : filteredStudents.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-muted-foreground">
                    {searchInput ? "No students match your search" : "No students enrolled in this class"}
                  </p>
                </div>
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Admission No.</TableHead>
                        <TableHead>Section</TableHead>
                        <TableHead>Roll No.</TableHead>
                        <TableHead>Gender</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredStudents.map((student) => (
                        <TableRow key={student.id}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center">
                                <span className="text-xs font-medium">
                                  {getStudentName(student).charAt(0).toUpperCase()}
                                </span>
                              </div>
                              <div>
                                <p className="font-medium">{getStudentName(student)}</p>
                                <p className="text-xs text-muted-foreground">
                                  {student.user?.email}
                                </p>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>{student.admission_number}</TableCell>
                          <TableCell>{getSectionName(student.section_id)}</TableCell>
                          <TableCell>{student.roll_number || "-"}</TableCell>
                          <TableCell className="capitalize">{student.gender}</TableCell>
                          <TableCell>
                            <Badge
                              variant="secondary"
                              className={statusColors[student.status] || ""}
                            >
                              {student.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <Link href={`/dashboard/students/${student.id}`}>
                              <Button variant="ghost" size="icon-sm">
                                <Eye className="h-4 w-4" />
                              </Button>
                            </Link>
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
        </TabsContent>


        {/* Sections Tab */}
        <TabsContent value="sections" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Sections</CardTitle>
              <CardDescription>
                {sections.length} section{sections.length !== 1 ? "s" : ""} in this class
              </CardDescription>
            </CardHeader>
            <CardContent>
              {sections.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-muted-foreground">No sections in this class</p>
                  {canManageClasses && (
                    <Link href={`/dashboard/classes/${classId}/edit`}>
                      <Button variant="link" className="mt-2">
                        Add sections
                      </Button>
                    </Link>
                  )}
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {sections.map((section) => (
                    <Card key={section.id}>
                      <CardContent className="pt-6">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-lg font-semibold">Section {section.name}</h3>
                          <Badge variant="outline">
                            {section.students_count}/{section.capacity}
                          </Badge>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Students</span>
                            <span>{section.students_count}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Capacity</span>
                            <span>{section.capacity}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Available</span>
                            <span>{section.capacity - section.students_count}</span>
                          </div>
                        </div>
                        <div className="mt-4">
                          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                section.students_count >= section.capacity
                                  ? "bg-red-500"
                                  : section.students_count >= section.capacity * 0.8
                                  ? "bg-yellow-500"
                                  : "bg-green-500"
                              }`}
                              style={{
                                width: `${Math.min(
                                  (section.students_count / section.capacity) * 100,
                                  100
                                )}%`,
                              }}
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Subjects Tab */}
        <TabsContent value="subjects" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Subjects</CardTitle>
              <CardDescription>
                {subjects.length} subject{subjects.length !== 1 ? "s" : ""} in this class
              </CardDescription>
            </CardHeader>
            <CardContent>
              {subjects.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-muted-foreground">No subjects assigned to this class</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Subject Name</TableHead>
                      <TableHead>Code</TableHead>
                      <TableHead>Credits</TableHead>
                      <TableHead>Teacher</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {subjects.map((subject) => (
                      <TableRow key={subject.id}>
                        <TableCell className="font-medium">{subject.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{subject.code}</Badge>
                        </TableCell>
                        <TableCell>{subject.credits}</TableCell>
                        <TableCell>{getTeacherName(subject.teacher)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Information Tab */}
        <TabsContent value="info" className="space-y-4">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Class Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Class Name</p>
                  <p className="font-medium">{classData.name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Grade Level</p>
                  <p className="font-medium">Grade {classData.grade_level}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Academic Year</p>
                  <p className="font-medium">{classData.academic_year}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Class Teacher</p>
                  <p className="font-medium">{getTeacherName(classData.class_teacher)}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Statistics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total Sections</p>
                  <p className="font-medium">{sections.length}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Students</p>
                  <p className="font-medium">{totalEnrolledStudents}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Capacity</p>
                  <p className="font-medium">{totalCapacity}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Occupancy Rate</p>
                  <p className="font-medium">
                    {totalCapacity > 0
                      ? `${((totalEnrolledStudents / totalCapacity) * 100).toFixed(1)}%`
                      : "N/A"}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
