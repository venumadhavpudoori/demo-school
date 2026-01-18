"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Save,
  Loader2,
  Users,
  BookOpen,
  Calculator,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

interface ClassListResponse {
  items: ClassItem[];
  total_count: number;
}

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
}

interface SubjectItem {
  id: number;
  name: string;
  code: string | null;
  class_id: number;
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

interface StudentListResponse {
  items: StudentListItem[];
  total_count: number;
}

interface GradeEntry {
  student_id: number;
  marks_obtained: string;
  remarks: string;
}

interface BulkGradeResponse {
  total_created: number;
  subject_id: number;
  exam_id: number;
  grades: Array<{
    id: number;
    student_id: number;
    marks_obtained: number;
    max_marks: number;
    percentage: number;
    grade: string | null;
  }>;
}

// Grade calculation helper
const calculateGrade = (percentage: number): string => {
  if (percentage >= 90) return "A+";
  if (percentage >= 80) return "A";
  if (percentage >= 70) return "B+";
  if (percentage >= 60) return "B";
  if (percentage >= 50) return "C";
  if (percentage >= 40) return "D";
  return "F";
};

const gradeColors: Record<string, string> = {
  "A+": "bg-green-100 text-green-800",
  A: "bg-green-100 text-green-800",
  "B+": "bg-blue-100 text-blue-800",
  B: "bg-blue-100 text-blue-800",
  C: "bg-yellow-100 text-yellow-800",
  D: "bg-orange-100 text-orange-800",
  F: "bg-red-100 text-red-800",
};

export default function GradeEntryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  // URL params
  const initialExamId = searchParams.get("exam_id") || "";
  const initialClassId = searchParams.get("class_id") || "";

  // Selection state
  const [selectedClassId, setSelectedClassId] = useState(initialClassId);
  const [selectedExamId, setSelectedExamId] = useState(initialExamId);
  const [selectedSubjectId, setSelectedSubjectId] = useState("");
  const [maxMarks, setMaxMarks] = useState("100");

  // Data state
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [exams, setExams] = useState<ExamListItem[]>([]);
  const [subjects, setSubjects] = useState<SubjectItem[]>([]);
  const [students, setStudents] = useState<StudentListItem[]>([]);

  // Grade entries
  const [gradeEntries, setGradeEntries] = useState<Map<number, GradeEntry>>(new Map());

  // UI state
  const [isLoadingClasses, setIsLoadingClasses] = useState(true);
  const [isLoadingExams, setIsLoadingExams] = useState(false);
  const [isLoadingSubjects, setIsLoadingSubjects] = useState(false);
  const [isLoadingStudents, setIsLoadingStudents] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Check permissions
  const canEnterGrades = user?.role === "admin" || user?.role === "super_admin" || user?.role === "teacher";

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

  // Fetch exams when class changes
  useEffect(() => {
    async function fetchExams() {
      if (!selectedClassId) {
        setExams([]);
        setSelectedExamId("");
        return;
      }
      setIsLoadingExams(true);
      try {
        const response = await api.get<ExamListResponse>("/api/exams", {
          class_id: parseInt(selectedClassId),
          page_size: 100,
        });
        setExams(response.items);
      } catch (err) {
        console.error("Failed to fetch exams:", err);
      } finally {
        setIsLoadingExams(false);
      }
    }
    fetchExams();
  }, [selectedClassId]);

  // Fetch subjects when class changes
  useEffect(() => {
    async function fetchSubjects() {
      if (!selectedClassId) {
        setSubjects([]);
        setSelectedSubjectId("");
        return;
      }
      setIsLoadingSubjects(true);
      try {
        // Subjects are fetched from class endpoint
        const response = await api.get<SubjectItem[]>(`/api/classes/${selectedClassId}/subjects`);
        setSubjects(response);
      } catch (err) {
        console.error("Failed to fetch subjects:", err);
        setSubjects([]);
      } finally {
        setIsLoadingSubjects(false);
      }
    }
    fetchSubjects();
  }, [selectedClassId]);

  // Fetch students when class changes
  useEffect(() => {
    async function fetchStudents() {
      if (!selectedClassId) {
        setStudents([]);
        setGradeEntries(new Map());
        return;
      }
      setIsLoadingStudents(true);
      try {
        const response = await api.get<StudentListResponse>("/api/students", {
          class_id: parseInt(selectedClassId),
          status: "active",
          page_size: 200,
        });
        setStudents(response.items);

        // Initialize grade entries
        const entries = new Map<number, GradeEntry>();
        response.items.forEach((student) => {
          entries.set(student.id, {
            student_id: student.id,
            marks_obtained: "",
            remarks: "",
          });
        });
        setGradeEntries(entries);
      } catch (err) {
        console.error("Failed to fetch students:", err);
      } finally {
        setIsLoadingStudents(false);
      }
    }
    fetchStudents();
  }, [selectedClassId]);

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

  // Update grade entry
  const updateGradeEntry = useCallback(
    (studentId: number, field: keyof GradeEntry, value: string) => {
      setGradeEntries((prev) => {
        const newEntries = new Map(prev);
        const existing = newEntries.get(studentId);
        if (existing) {
          newEntries.set(studentId, { ...existing, [field]: value });
        }
        return newEntries;
      });
    },
    []
  );

  // Calculate percentage and grade for a student
  const getCalculatedGrade = (marks: string) => {
    const marksNum = parseFloat(marks);
    const maxMarksNum = parseFloat(maxMarks);
    if (isNaN(marksNum) || isNaN(maxMarksNum) || maxMarksNum === 0) {
      return { percentage: 0, grade: "-" };
    }
    const percentage = (marksNum / maxMarksNum) * 100;
    return { percentage, grade: calculateGrade(percentage) };
  };

  // Handle save grades
  const handleSaveGrades = async () => {
    if (!selectedExamId || !selectedSubjectId) {
      toast.error("Please select an exam and subject");
      return;
    }

    const maxMarksNum = parseFloat(maxMarks);
    if (isNaN(maxMarksNum) || maxMarksNum <= 0) {
      toast.error("Please enter valid maximum marks");
      return;
    }

    // Filter entries with marks
    const validEntries = Array.from(gradeEntries.values()).filter(
      (entry) => entry.marks_obtained.trim() !== ""
    );

    if (validEntries.length === 0) {
      toast.error("Please enter marks for at least one student");
      return;
    }

    // Validate marks
    for (const entry of validEntries) {
      const marks = parseFloat(entry.marks_obtained);
      if (isNaN(marks) || marks < 0 || marks > maxMarksNum) {
        toast.error(`Invalid marks for student. Marks must be between 0 and ${maxMarksNum}`);
        return;
      }
    }

    setIsSaving(true);
    try {
      const response = await api.post<BulkGradeResponse>("/api/grades/bulk", {
        subject_id: parseInt(selectedSubjectId),
        exam_id: parseInt(selectedExamId),
        max_marks: maxMarksNum,
        grades: validEntries.map((entry) => ({
          student_id: entry.student_id,
          marks_obtained: parseFloat(entry.marks_obtained),
          remarks: entry.remarks || null,
        })),
      });

      toast.success(`Grades saved for ${response.total_created} students`);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to save grades");
    } finally {
      setIsSaving(false);
    }
  };

  // Get summary stats
  const getSummaryStats = () => {
    const entries = Array.from(gradeEntries.values()).filter(
      (e) => e.marks_obtained.trim() !== ""
    );
    if (entries.length === 0) return null;

    const marks = entries.map((e) => parseFloat(e.marks_obtained)).filter((m) => !isNaN(m));
    const maxMarksNum = parseFloat(maxMarks) || 100;

    const avg = marks.reduce((a, b) => a + b, 0) / marks.length;
    const highest = Math.max(...marks);
    const lowest = Math.min(...marks);
    const passCount = marks.filter((m) => (m / maxMarksNum) * 100 >= 40).length;

    return {
      entered: entries.length,
      total: students.length,
      average: avg.toFixed(1),
      highest,
      lowest,
      passCount,
      passPercentage: ((passCount / entries.length) * 100).toFixed(1),
    };
  };

  const stats = getSummaryStats();

  if (!canEnterGrades) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">
          You don&apos;t have permission to enter grades.
        </p>
      </div>
    );
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
          <h1 className="text-2xl font-bold">Enter Grades</h1>
          <p className="text-muted-foreground">
            Record student grades for an exam
          </p>
        </div>
      </div>

      {/* Selection Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Select Class, Exam & Subject</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-5">
            {/* Class Selector */}
            <div>
              <Label className="mb-2 block">Class *</Label>
              {isLoadingClasses ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <select
                  value={selectedClassId}
                  onChange={(e) => {
                    setSelectedClassId(e.target.value);
                    setSelectedExamId("");
                    setSelectedSubjectId("");
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

            {/* Exam Selector */}
            <div>
              <Label className="mb-2 block">Exam *</Label>
              {isLoadingExams ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <select
                  value={selectedExamId}
                  onChange={(e) => setSelectedExamId(e.target.value)}
                  disabled={!selectedClassId}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm disabled:opacity-50"
                >
                  <option value="">Select Exam</option>
                  {exams.map((exam) => (
                    <option key={exam.id} value={exam.id}>
                      {exam.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Subject Selector */}
            <div>
              <Label className="mb-2 block">Subject *</Label>
              {isLoadingSubjects ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <select
                  value={selectedSubjectId}
                  onChange={(e) => setSelectedSubjectId(e.target.value)}
                  disabled={!selectedClassId}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm disabled:opacity-50"
                >
                  <option value="">Select Subject</option>
                  {subjects.map((subject) => (
                    <option key={subject.id} value={subject.id}>
                      {subject.name} {subject.code ? `(${subject.code})` : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Max Marks */}
            <div>
              <Label className="mb-2 block">Max Marks *</Label>
              <Input
                type="number"
                value={maxMarks}
                onChange={(e) => setMaxMarks(e.target.value)}
                min="1"
                placeholder="100"
              />
            </div>

            {/* Save Button */}
            <div className="flex items-end">
              <Button
                onClick={handleSaveGrades}
                disabled={isSaving || !selectedExamId || !selectedSubjectId}
                className="w-full"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save Grades
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Stats */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-5">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Entered</p>
                  <p className="text-2xl font-bold">
                    {stats.entered}/{stats.total}
                  </p>
                </div>
                <Users className="h-8 w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Average</p>
                  <p className="text-2xl font-bold">{stats.average}</p>
                </div>
                <Calculator className="h-8 w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div>
                <p className="text-sm text-muted-foreground">Highest</p>
                <p className="text-2xl font-bold">{stats.highest}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div>
                <p className="text-sm text-muted-foreground">Lowest</p>
                <p className="text-2xl font-bold">{stats.lowest}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div>
                <p className="text-sm text-muted-foreground">Pass Rate</p>
                <p className="text-2xl font-bold">{stats.passPercentage}%</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Grade Entry Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Student Grades
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
                Please select a class to enter grades
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
                  <Skeleton className="h-9 w-24" />
                </div>
              ))}
            </div>
          ) : students.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                No students found in this class
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">Roll</TableHead>
                  <TableHead>Student Name</TableHead>
                  <TableHead>Admission No.</TableHead>
                  <TableHead className="w-32">Marks</TableHead>
                  <TableHead className="w-24">%</TableHead>
                  <TableHead className="w-20">Grade</TableHead>
                  <TableHead>Remarks</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {students.map((student) => {
                  const entry = gradeEntries.get(student.id);
                  const { percentage, grade } = getCalculatedGrade(
                    entry?.marks_obtained || ""
                  );
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
                        <Input
                          type="number"
                          value={entry?.marks_obtained || ""}
                          onChange={(e) =>
                            updateGradeEntry(student.id, "marks_obtained", e.target.value)
                          }
                          min="0"
                          max={maxMarks}
                          placeholder="0"
                          className="w-24"
                        />
                      </TableCell>
                      <TableCell>
                        {entry?.marks_obtained ? `${percentage.toFixed(1)}%` : "-"}
                      </TableCell>
                      <TableCell>
                        {entry?.marks_obtained ? (
                          <Badge
                            variant="secondary"
                            className={gradeColors[grade] || ""}
                          >
                            {grade}
                          </Badge>
                        ) : (
                          "-"
                        )}
                      </TableCell>
                      <TableCell>
                        <Input
                          value={entry?.remarks || ""}
                          onChange={(e) =>
                            updateGradeEntry(student.id, "remarks", e.target.value)
                          }
                          placeholder="Optional remarks"
                          className="w-full"
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
