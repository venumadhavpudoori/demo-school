"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Calendar,
  Check,
  X,
  Clock,
  AlertCircle,
  Save,
  Users,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
interface ClassItem {
  id: number;
  name: string;
  grade_level: number;
  academic_year: string;
}

interface SectionItem {
  id: number;
  class_id: number;
  name: string;
}

interface StudentListItem {
  id: number;
  admission_number: string;
  roll_number: number | null;
  user: {
    id: number;
    email: string;
    profile_data: Record<string, unknown>;
  } | null;
}

interface AttendanceRecord {
  student_id: number;
  status: "present" | "absent" | "late" | "half_day" | "excused";
  remarks: string;
}

interface ClassListResponse {
  items: ClassItem[];
  total_count: number;
}

interface SectionListResponse {
  items: SectionItem[];
  total_count: number;
}

interface StudentListResponse {
  items: StudentListItem[];
  total_count: number;
}

interface BulkAttendanceResponse {
  total_marked: number;
  date: string;
  class_id: number;
  section_id: number | null;
  status_counts: Record<string, number>;
}

const statusConfig = {
  present: { label: "Present", color: "bg-green-100 text-green-800", icon: Check },
  absent: { label: "Absent", color: "bg-red-100 text-red-800", icon: X },
  late: { label: "Late", color: "bg-yellow-100 text-yellow-800", icon: Clock },
  half_day: { label: "Half Day", color: "bg-orange-100 text-orange-800", icon: AlertCircle },
  excused: { label: "Excused", color: "bg-blue-100 text-blue-800", icon: AlertCircle },
};

export default function AttendanceMarkingPage() {
  const router = useRouter();
  const { user } = useAuth();

  // State
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [sections, setSections] = useState<SectionItem[]>([]);
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [isLoadingClasses, setIsLoadingClasses] = useState(true);
  const [isLoadingSections, setIsLoadingSections] = useState(false);
  const [isLoadingStudents, setIsLoadingStudents] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Selection state
  const [selectedClassId, setSelectedClassId] = useState<string>("");
  const [selectedSectionId, setSelectedSectionId] = useState<string>("");
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );

  // Attendance records state
  const [attendanceRecords, setAttendanceRecords] = useState<Map<number, AttendanceRecord>>(
    new Map()
  );

  // Check permissions
  const canMarkAttendance = user?.role === "admin" || user?.role === "super_admin" || user?.role === "teacher";

  // Fetch classes
  useEffect(() => {
    async function fetchClasses() {
      try {
        const response = await api.get<ClassListResponse>("/api/classes", {
          page_size: 100,
        });
        setClasses(response.items);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch classes");
      } finally {
        setIsLoadingClasses(false);
      }
    }
    fetchClasses();
  }, []);

  // Fetch sections when class changes
  useEffect(() => {
    async function fetchSections() {
      if (!selectedClassId) {
        setSections([]);
        setSelectedSectionId("");
        return;
      }
      setIsLoadingSections(true);
      try {
        const response = await api.get<SectionListResponse>("/api/sections", {
          class_id: parseInt(selectedClassId),
          page_size: 100,
        });
        setSections(response.items);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch sections");
      } finally {
        setIsLoadingSections(false);
      }
    }
    fetchSections();
  }, [selectedClassId]);

  // Fetch students when class/section changes
  useEffect(() => {
    async function fetchStudents() {
      if (!selectedClassId) {
        setStudents([]);
        setAttendanceRecords(new Map());
        return;
      }
      setIsLoadingStudents(true);
      try {
        const params: Record<string, string | number> = {
          class_id: parseInt(selectedClassId),
          status: "active",
          page_size: 100,
        };
        if (selectedSectionId) {
          params.section_id = parseInt(selectedSectionId);
        }
        const response = await api.get<StudentListResponse>("/api/students", params);
        setStudents(response.items);
        
        // Initialize attendance records with default "present" status
        const initialRecords = new Map<number, AttendanceRecord>();
        response.items.forEach((student) => {
          initialRecords.set(student.id, {
            student_id: student.id,
            status: "present",
            remarks: "",
          });
        });
        setAttendanceRecords(initialRecords);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch students");
      } finally {
        setIsLoadingStudents(false);
      }
    }
    fetchStudents();
  }, [selectedClassId, selectedSectionId]);

  // Get student name
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

  // Update attendance status for a student
  const updateAttendanceStatus = useCallback(
    (studentId: number, status: AttendanceRecord["status"]) => {
      setAttendanceRecords((prev) => {
        const newRecords = new Map(prev);
        const existing = newRecords.get(studentId);
        newRecords.set(studentId, {
          student_id: studentId,
          status,
          remarks: existing?.remarks || "",
        });
        return newRecords;
      });
    },
    []
  );

  // Mark all students with a status
  const markAllAs = useCallback((status: AttendanceRecord["status"]) => {
    setAttendanceRecords((prev) => {
      const newRecords = new Map(prev);
      students.forEach((student) => {
        const existing = newRecords.get(student.id);
        newRecords.set(student.id, {
          student_id: student.id,
          status,
          remarks: existing?.remarks || "",
        });
      });
      return newRecords;
    });
  }, [students]);

  // Save attendance
  const handleSaveAttendance = async () => {
    if (!selectedClassId || students.length === 0) {
      toast.error("Please select a class and ensure students are loaded");
      return;
    }

    setIsSaving(true);
    try {
      const records = Array.from(attendanceRecords.values());
      const response = await api.post<BulkAttendanceResponse>("/api/attendance/mark", {
        class_id: parseInt(selectedClassId),
        section_id: selectedSectionId ? parseInt(selectedSectionId) : null,
        date: selectedDate,
        records,
      });

      toast.success(`Attendance marked for ${response.total_marked} students`);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to save attendance");
    } finally {
      setIsSaving(false);
    }
  };

  // Get status counts
  const getStatusCounts = () => {
    const counts: Record<string, number> = {
      present: 0,
      absent: 0,
      late: 0,
      half_day: 0,
      excused: 0,
    };
    attendanceRecords.forEach((record) => {
      counts[record.status]++;
    });
    return counts;
  };

  const statusCounts = getStatusCounts();

  if (!canMarkAttendance) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">
          You don&apos;t have permission to mark attendance.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Mark Attendance</h1>
          <p className="text-muted-foreground">
            Record daily attendance for students
          </p>
        </div>
        <Button variant="outline" onClick={() => router.push("/attendance/history")}>
          <Calendar className="h-4 w-4 mr-2" />
          View History
        </Button>
      </div>

      {/* Selection Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Select Class & Date</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            {/* Date Picker */}
            <div>
              <label className="text-sm font-medium mb-2 block">Date</label>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
              />
            </div>

            {/* Class Selector */}
            <div>
              <label className="text-sm font-medium mb-2 block">Class</label>
              {isLoadingClasses ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <select
                  value={selectedClassId}
                  onChange={(e) => {
                    setSelectedClassId(e.target.value);
                    setSelectedSectionId("");
                  }}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                >
                  <option value="">Select Class</option>
                  {classes.map((cls) => (
                    <option key={cls.id} value={cls.id}>
                      {cls.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Section Selector */}
            <div>
              <label className="text-sm font-medium mb-2 block">Section</label>
              {isLoadingSections ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <select
                  value={selectedSectionId}
                  onChange={(e) => setSelectedSectionId(e.target.value)}
                  disabled={!selectedClassId}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm disabled:opacity-50"
                >
                  <option value="">All Sections</option>
                  {sections.map((section) => (
                    <option key={section.id} value={section.id}>
                      {section.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Quick Actions */}
            <div>
              <label className="text-sm font-medium mb-2 block">Quick Actions</label>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => markAllAs("present")}
                  disabled={students.length === 0}
                >
                  All Present
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => markAllAs("absent")}
                  disabled={students.length === 0}
                >
                  All Absent
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Status Summary */}
      {students.length > 0 && (
        <div className="grid gap-4 md:grid-cols-5">
          {Object.entries(statusConfig).map(([status, config]) => (
            <Card key={status}>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{config.label}</p>
                    <p className="text-2xl font-bold">
                      {statusCounts[status as keyof typeof statusCounts]}
                    </p>
                  </div>
                  <div className={`p-2 rounded-full ${config.color}`}>
                    <config.icon className="h-4 w-4" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Attendance Grid */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Student Attendance
            </span>
            {students.length > 0 && (
              <span className="text-sm font-normal text-muted-foreground">
                {students.length} student{students.length !== 1 ? "s" : ""}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!selectedClassId ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                Please select a class to mark attendance
              </p>
            </div>
          ) : isLoadingStudents ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                  <Skeleton className="h-8 w-32" />
                </div>
              ))}
            </div>
          ) : students.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                No students found in this class/section
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">Roll</TableHead>
                  <TableHead>Student Name</TableHead>
                  <TableHead>Admission No.</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {students.map((student) => {
                  const record = attendanceRecords.get(student.id);
                  return (
                    <TableRow key={student.id}>
                      <TableCell className="font-medium">
                        {student.roll_number || "-"}
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium">{getStudentName(student)}</p>
                          <p className="text-sm text-muted-foreground">
                            {student.user?.email}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>{student.admission_number}</TableCell>
                      <TableCell>
                        <div className="flex justify-center gap-1">
                          {Object.entries(statusConfig).map(([status, config]) => (
                            <Button
                              key={status}
                              variant={record?.status === status ? "default" : "outline"}
                              size="icon-sm"
                              onClick={() =>
                                updateAttendanceStatus(
                                  student.id,
                                  status as AttendanceRecord["status"]
                                )
                              }
                              className={
                                record?.status === status
                                  ? config.color
                                  : ""
                              }
                              title={config.label}
                            >
                              <config.icon className="h-4 w-4" />
                            </Button>
                          ))}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}

          {/* Save Button */}
          {students.length > 0 && (
            <div className="flex justify-end mt-6 pt-4 border-t">
              <Button onClick={handleSaveAttendance} disabled={isSaving}>
                <Save className="h-4 w-4 mr-2" />
                {isSaving ? "Saving..." : "Save Attendance"}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
