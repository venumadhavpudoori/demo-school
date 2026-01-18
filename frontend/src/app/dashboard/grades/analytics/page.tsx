"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Users,
  Award,
  Filter,
  X,
  Download,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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

// Types based on backend schema
interface ReportFilters {
  class_id: number | null;
  section_id: number | null;
  exam_id: number | null;
  subject_id: number | null;
  academic_year: string | null;
  start_date: string | null;
  end_date: string | null;
  fee_type: string | null;
}

interface GradeAnalysisSummary {
  class_id: number | null;
  class_name: string | null;
  exam_id: number | null;
  exam_name: string | null;
  total_students: number;
  total_grades: number | null;
  average_percentage: number;
  highest_percentage: number;
  lowest_percentage: number;
  pass_count: number;
  fail_count: number;
  pass_percentage: number;
}


interface SubjectAnalytics {
  subject_id: number;
  subject_name: string;
  total_students: number;
  average_marks: number;
  average_percentage: number;
  highest_marks: number;
  lowest_marks: number;
  pass_count: number;
  fail_count: number;
  pass_percentage: number;
  grade_distribution: Record<string, number>;
}

interface StudentRanking {
  rank: number | null;
  student_id: number;
  student_name: string | null;
  total_marks: number;
  total_max_marks: number | null;
  percentage: number;
  grade: string;
}

interface GradeAnalysisResponse {
  report_type: string;
  filters: ReportFilters;
  summary: GradeAnalysisSummary;
  grade_distribution: Record<string, number>;
  subject_analytics: SubjectAnalytics[] | null;
  student_rankings: StudentRanking[] | null;
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


const gradeColors: Record<string, string> = {
  "A+": "bg-green-500",
  A: "bg-green-400",
  "B+": "bg-blue-500",
  B: "bg-blue-400",
  C: "bg-yellow-500",
  D: "bg-orange-500",
  F: "bg-red-500",
};

const gradeBadgeColors: Record<string, string> = {
  "A+": "bg-green-100 text-green-800 border-green-200",
  A: "bg-green-100 text-green-800 border-green-200",
  "B+": "bg-blue-100 text-blue-800 border-blue-200",
  B: "bg-blue-100 text-blue-800 border-blue-200",
  C: "bg-yellow-100 text-yellow-800 border-yellow-200",
  D: "bg-orange-100 text-orange-800 border-orange-200",
  F: "bg-red-100 text-red-800 border-red-200",
};

// Simple bar chart component
function GradeDistributionChart({ distribution }: { distribution: Record<string, number> }) {
  const grades = ["A+", "A", "B+", "B", "C", "D", "F"];
  const maxCount = Math.max(...Object.values(distribution), 1);
  const total = Object.values(distribution).reduce((sum, count) => sum + count, 0);

  return (
    <div className="space-y-3">
      {grades.map((grade) => {
        const count = distribution[grade] || 0;
        const percentage = total > 0 ? (count / total) * 100 : 0;
        const barWidth = maxCount > 0 ? (count / maxCount) * 100 : 0;

        return (
          <div key={grade} className="flex items-center gap-3">
            <div className="w-8 text-sm font-medium">{grade}</div>
            <div className="flex-1 h-6 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full ${gradeColors[grade] || "bg-gray-400"} transition-all duration-500`}
                style={{ width: `${barWidth}%` }}
              />
            </div>
            <div className="w-16 text-sm text-right">
              {count} ({percentage.toFixed(0)}%)
            </div>
          </div>
        );
      })}
    </div>
  );
}


// Subject performance chart component
function SubjectPerformanceChart({ subjects }: { subjects: SubjectAnalytics[] }) {
  if (subjects.length === 0) return null;

  const maxPercentage = 100;

  return (
    <div className="space-y-4">
      {subjects.map((subject) => (
        <div key={subject.subject_id} className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{subject.subject_name}</span>
            <span className="text-sm text-muted-foreground">
              Avg: {subject.average_percentage.toFixed(1)}%
            </span>
          </div>
          <div className="relative h-8 bg-muted rounded-lg overflow-hidden">
            {/* Average bar */}
            <div
              className="absolute h-full bg-primary/70 transition-all duration-500"
              style={{ width: `${(subject.average_percentage / maxPercentage) * 100}%` }}
            />
            {/* Highest marker */}
            <div
              className="absolute top-0 h-full w-0.5 bg-green-500"
              style={{ left: `${(subject.highest_marks / (subject.highest_marks || 100)) * (subject.average_percentage / maxPercentage) * 100}%` }}
              title={`Highest: ${subject.highest_marks}`}
            />
            {/* Pass rate indicator */}
            <div className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-medium">
              {subject.pass_percentage.toFixed(0)}% pass
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function GradeAnalyticsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  // State
  const [analytics, setAnalytics] = useState<GradeAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [exams, setExams] = useState<ExamListItem[]>([]);
  const [showFilters, setShowFilters] = useState(true);

  // Filter state from URL params
  const classId = searchParams.get("class_id") || "";
  const examId = searchParams.get("exam_id") || "";
  const academicYear = searchParams.get("academic_year") || "";

  // Local filter state
  const [classFilter, setClassFilter] = useState(classId);
  const [examFilter, setExamFilter] = useState(examId);
  const [academicYearFilter, setAcademicYearFilter] = useState(academicYear);


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
      router.push(`/grades/analytics?${params.toString()}`);
    },
    [router, searchParams]
  );

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
      }
    }
    fetchClasses();
  }, []);

  // Fetch exams when class changes
  useEffect(() => {
    async function fetchExams() {
      if (!classFilter) {
        setExams([]);
        return;
      }
      try {
        const response = await api.get<ExamListResponse>("/api/exams", {
          class_id: parseInt(classFilter),
          page_size: 100,
        });
        setExams(response.items);
      } catch (err) {
        console.error("Failed to fetch exams:", err);
      }
    }
    fetchExams();
  }, [classFilter]);


  // Fetch analytics data
  useEffect(() => {
    async function fetchAnalytics() {
      // Only fetch if we have at least class_id
      if (!classId) {
        setAnalytics(null);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {};
        if (classId) params.class_id = parseInt(classId);
        if (examId) params.exam_id = parseInt(examId);
        if (academicYear) params.academic_year = academicYear;

        const response = await api.get<GradeAnalysisResponse>(
          "/api/reports/grade-analysis",
          params
        );
        setAnalytics(response);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch grade analytics");
        setAnalytics(null);
      } finally {
        setIsLoading(false);
      }
    }
    fetchAnalytics();
  }, [classId, examId, academicYear]);

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({
      class_id: classFilter,
      exam_id: examFilter,
      academic_year: academicYearFilter,
    });
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setClassFilter("");
    setExamFilter("");
    setAcademicYearFilter("");
    router.push("/grades/analytics");
  };

  // Handle export
  const handleExport = async (format: "csv" | "pdf") => {
    if (!classId) {
      toast.error("Please select a class to export");
      return;
    }

    setIsExporting(true);
    try {
      const response = await api.post<Blob>("/api/reports/export", {
        report_type: "grade_analysis",
        format,
        class_id: classId ? parseInt(classId) : null,
        exam_id: examId ? parseInt(examId) : null,
        academic_year: academicYear || null,
      });

      // For CSV, trigger download
      if (format === "csv") {
        const blob = new Blob([response as unknown as string], { type: "text/csv" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `grade_analysis_${new Date().toISOString().split("T")[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }

      toast.success(`Report exported as ${format.toUpperCase()}`);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to export report");
    } finally {
      setIsExporting(false);
    }
  };

  // Check if any filters are active
  const hasActiveFilters = classId || examId || academicYear;

  // Get unique academic years from classes
  const academicYears = [...new Set(classes.map((c) => c.academic_year))].sort().reverse();


  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/grades">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Grade Analytics</h1>
            <p className="text-muted-foreground">
              Analyze student performance and grade distribution
            </p>
          </div>
        </div>
        {analytics && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => handleExport("csv")}
              disabled={isExporting}
            >
              {isExporting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Download className="h-4 w-4 mr-2" />
              )}
              Export CSV
            </Button>
          </div>
        )}
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Filter className="h-4 w-4" />
              Filters
            </CardTitle>
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={handleClearFilters}>
                <X className="h-4 w-4 mr-2" />
                Clear
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Class *</label>
              <select
                value={classFilter}
                onChange={(e) => {
                  setClassFilter(e.target.value);
                  setExamFilter("");
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
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Exam</label>
              <select
                value={examFilter}
                onChange={(e) => setExamFilter(e.target.value)}
                disabled={!classFilter}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm disabled:opacity-50"
              >
                <option value="">All Exams</option>
                {exams.map((exam) => (
                  <option key={exam.id} value={exam.id}>
                    {exam.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Academic Year</label>
              <select
                value={academicYearFilter}
                onChange={(e) => setAcademicYearFilter(e.target.value)}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
              >
                <option value="">All Years</option>
                {academicYears.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <Button onClick={handleApplyFilters} className="w-full">
                Apply Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>


      {/* No class selected state */}
      {!classId && !isLoading && (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">Select a Class</h3>
              <p className="text-muted-foreground">
                Choose a class from the filters above to view grade analytics
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <Skeleton className="h-4 w-24 mb-2" />
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Analytics Content */}
      {analytics && !isLoading && (
        <>
          {/* Summary Cards */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <Users className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Students</p>
                    <p className="text-2xl font-bold">{analytics.summary.total_students}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-green-100 rounded-lg">
                    <TrendingUp className="h-6 w-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Average Score</p>
                    <p className="text-2xl font-bold">
                      {analytics.summary.average_percentage.toFixed(1)}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-purple-100 rounded-lg">
                    <Award className="h-6 w-6 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Pass Rate</p>
                    <p className="text-2xl font-bold">
                      {analytics.summary.pass_percentage.toFixed(1)}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-lg ${
                    analytics.summary.fail_count > 0 ? "bg-red-100" : "bg-green-100"
                  }`}>
                    <TrendingDown className={`h-6 w-6 ${
                      analytics.summary.fail_count > 0 ? "text-red-600" : "text-green-600"
                    }`} />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Failed Students</p>
                    <p className="text-2xl font-bold">{analytics.summary.fail_count}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>


          {/* Charts Row */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Grade Distribution Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Grade Distribution
                </CardTitle>
                <CardDescription>
                  Distribution of grades across all students
                </CardDescription>
              </CardHeader>
              <CardContent>
                <GradeDistributionChart distribution={analytics.grade_distribution} />
              </CardContent>
            </Card>

            {/* Performance Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Performance Summary</CardTitle>
                <CardDescription>
                  Key performance metrics for {analytics.summary.class_name || "selected class"}
                  {analytics.summary.exam_name && ` - ${analytics.summary.exam_name}`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 bg-muted rounded-lg">
                    <span className="text-sm">Highest Score</span>
                    <span className="font-bold text-green-600">
                      {analytics.summary.highest_percentage.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-muted rounded-lg">
                    <span className="text-sm">Lowest Score</span>
                    <span className="font-bold text-red-600">
                      {analytics.summary.lowest_percentage.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-muted rounded-lg">
                    <span className="text-sm">Class Average</span>
                    <span className="font-bold">
                      {analytics.summary.average_percentage.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-muted rounded-lg">
                    <span className="text-sm">Pass / Fail</span>
                    <span className="font-bold">
                      <span className="text-green-600">{analytics.summary.pass_count}</span>
                      {" / "}
                      <span className="text-red-600">{analytics.summary.fail_count}</span>
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>


          {/* Subject Analytics */}
          {analytics.subject_analytics && analytics.subject_analytics.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Subject-wise Performance</CardTitle>
                <CardDescription>
                  Performance breakdown by subject
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Subject</TableHead>
                      <TableHead className="text-center">Students</TableHead>
                      <TableHead className="text-right">Avg %</TableHead>
                      <TableHead className="text-right">Highest</TableHead>
                      <TableHead className="text-right">Lowest</TableHead>
                      <TableHead className="text-center">Pass Rate</TableHead>
                      <TableHead className="text-center">Grade Distribution</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {analytics.subject_analytics.map((subject) => (
                      <TableRow key={subject.subject_id}>
                        <TableCell className="font-medium">
                          {subject.subject_name}
                        </TableCell>
                        <TableCell className="text-center">
                          {subject.total_students}
                        </TableCell>
                        <TableCell className="text-right">
                          {subject.average_percentage.toFixed(1)}%
                        </TableCell>
                        <TableCell className="text-right text-green-600">
                          {subject.highest_marks}
                        </TableCell>
                        <TableCell className="text-right text-red-600">
                          {subject.lowest_marks}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge
                            variant="outline"
                            className={
                              subject.pass_percentage >= 80
                                ? "bg-green-100 text-green-800"
                                : subject.pass_percentage >= 60
                                ? "bg-yellow-100 text-yellow-800"
                                : "bg-red-100 text-red-800"
                            }
                          >
                            {subject.pass_percentage.toFixed(0)}%
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1 justify-center">
                            {Object.entries(subject.grade_distribution).map(([grade, count]) => (
                              count > 0 && (
                                <Badge
                                  key={grade}
                                  variant="outline"
                                  className={`text-xs ${gradeBadgeColors[grade] || ""}`}
                                >
                                  {grade}: {count}
                                </Badge>
                              )
                            ))}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}


          {/* Student Rankings */}
          {analytics.student_rankings && analytics.student_rankings.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Award className="h-5 w-5" />
                  Student Rankings
                </CardTitle>
                <CardDescription>
                  Top performing students based on overall percentage
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16">Rank</TableHead>
                      <TableHead>Student</TableHead>
                      <TableHead className="text-right">Total Marks</TableHead>
                      <TableHead className="text-right">Percentage</TableHead>
                      <TableHead className="text-center">Grade</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {analytics.student_rankings.slice(0, 20).map((student, index) => (
                      <TableRow key={student.student_id}>
                        <TableCell>
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                            index === 0
                              ? "bg-yellow-100 text-yellow-800"
                              : index === 1
                              ? "bg-gray-100 text-gray-800"
                              : index === 2
                              ? "bg-orange-100 text-orange-800"
                              : "bg-muted"
                          }`}>
                            {student.rank || index + 1}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Link
                            href={`/grades/report-card/${student.student_id}`}
                            className="font-medium hover:underline"
                          >
                            {student.student_name || `Student #${student.student_id}`}
                          </Link>
                        </TableCell>
                        <TableCell className="text-right">
                          {student.total_marks}
                          {student.total_max_marks && (
                            <span className="text-muted-foreground">
                              /{student.total_max_marks}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {student.percentage.toFixed(1)}%
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge
                            variant="outline"
                            className={gradeBadgeColors[student.grade] || ""}
                          >
                            {student.grade}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {analytics.student_rankings.length > 20 && (
                  <p className="text-sm text-muted-foreground text-center mt-4">
                    Showing top 20 of {analytics.student_rankings.length} students
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
