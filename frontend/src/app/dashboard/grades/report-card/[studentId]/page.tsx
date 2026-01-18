"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Printer,
  Download,
  GraduationCap,
  User,
  Calendar,
  BookOpen,
  Award,
  TrendingUp,
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
interface SubjectGrade {
  subject_id: number;
  subject_name: string;
  subject_code: string | null;
  marks_obtained: number;
  max_marks: number;
  percentage: number;
  grade: string | null;
  remarks: string | null;
}

interface ExamResult {
  exam_id: number;
  exam_name: string;
  exam_type: string;
  subject_grades: SubjectGrade[];
  total_marks_obtained: number;
  total_max_marks: number;
  overall_percentage: number;
  overall_grade: string | null;
}

interface ReportCardResponse {
  student_id: number;
  student_name: string;
  admission_number: string;
  class_id: number;
  class_name: string;
  section_id: number | null;
  section_name: string | null;
  academic_year: string;
  exam_results: ExamResult[];
  cumulative_percentage: number | null;
  cumulative_grade: string | null;
}

const examTypeLabels: Record<string, string> = {
  unit_test: "Unit Test",
  midterm: "Midterm",
  final: "Final",
  quarterly: "Quarterly",
  half_yearly: "Half Yearly",
  annual: "Annual",
};

const gradeColors: Record<string, string> = {
  "A+": "bg-green-100 text-green-800 border-green-200",
  A: "bg-green-100 text-green-800 border-green-200",
  "B+": "bg-blue-100 text-blue-800 border-blue-200",
  B: "bg-blue-100 text-blue-800 border-blue-200",
  C: "bg-yellow-100 text-yellow-800 border-yellow-200",
  D: "bg-orange-100 text-orange-800 border-orange-200",
  F: "bg-red-100 text-red-800 border-red-200",
};

export default function ReportCardPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const studentId = params.studentId as string;
  const academicYear = searchParams.get("academic_year") || undefined;
  const { user } = useAuth();
  const printRef = useRef<HTMLDivElement>(null);

  const [reportCard, setReportCard] = useState<ReportCardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isPrinting, setIsPrinting] = useState(false);

  // Fetch report card
  useEffect(() => {
    async function fetchReportCard() {
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {};
        if (academicYear) {
          params.academic_year = academicYear;
        }
        const response = await api.get<ReportCardResponse>(
          `/api/grades/report-card/${studentId}`,
          params
        );
        setReportCard(response);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch report card");
        router.push("/grades");
      } finally {
        setIsLoading(false);
      }
    }
    fetchReportCard();
  }, [studentId, academicYear, router]);

  // Handle print
  const handlePrint = () => {
    setIsPrinting(true);
    setTimeout(() => {
      window.print();
      setIsPrinting(false);
    }, 100);
  };

  // Get grade badge color
  const getGradeColor = (grade: string | null) => {
    if (!grade) return "bg-gray-100 text-gray-800 border-gray-200";
    return gradeColors[grade] || "bg-gray-100 text-gray-800 border-gray-200";
  };

  // Calculate performance indicator
  const getPerformanceIndicator = (percentage: number) => {
    if (percentage >= 90) return { label: "Excellent", color: "text-green-600" };
    if (percentage >= 80) return { label: "Very Good", color: "text-blue-600" };
    if (percentage >= 70) return { label: "Good", color: "text-cyan-600" };
    if (percentage >= 60) return { label: "Satisfactory", color: "text-yellow-600" };
    if (percentage >= 40) return { label: "Needs Improvement", color: "text-orange-600" };
    return { label: "Below Average", color: "text-red-600" };
  };

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
        <Skeleton className="h-64" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!reportCard) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <p className="text-muted-foreground">Report card not found</p>
        <Link href="/grades">
          <Button variant="outline">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Grades
          </Button>
        </Link>
      </div>
    );
  }

  const performance = reportCard.cumulative_percentage
    ? getPerformanceIndicator(reportCard.cumulative_percentage)
    : null;

  return (
    <div className="space-y-6">
      {/* Header - Hidden when printing */}
      <div className="flex items-center justify-between print:hidden">
        <div className="flex items-center gap-4">
          <Link href="/grades">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Report Card</h1>
            <p className="text-muted-foreground">
              Academic performance report for {reportCard.student_name}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handlePrint} disabled={isPrinting}>
            {isPrinting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Printer className="h-4 w-4 mr-2" />
            )}
            Print
          </Button>
        </div>
      </div>

      {/* Printable Report Card */}
      <div ref={printRef} className="print:p-8">
        {/* School Header - Visible when printing */}
        <div className="hidden print:block text-center mb-8 border-b-2 border-gray-800 pb-4">
          <h1 className="text-2xl font-bold">SCHOOL ERP SYSTEM</h1>
          <p className="text-lg">Academic Report Card</p>
          <p className="text-sm text-muted-foreground">
            Academic Year: {reportCard.academic_year}
          </p>
        </div>

        {/* Student Information Card */}
        <Card className="print:shadow-none print:border-2">
          <CardHeader className="print:pb-2">
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Student Information
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div>
                <p className="text-sm text-muted-foreground">Student Name</p>
                <p className="font-medium">{reportCard.student_name}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Admission Number</p>
                <p className="font-medium">{reportCard.admission_number}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Class</p>
                <p className="font-medium">
                  {reportCard.class_name}
                  {reportCard.section_name && ` - ${reportCard.section_name}`}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Academic Year</p>
                <p className="font-medium">{reportCard.academic_year}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Cumulative Performance Summary */}
        {reportCard.cumulative_percentage !== null && (
          <Card className="print:shadow-none print:border-2 print:mt-4">
            <CardHeader className="print:pb-2">
              <CardTitle className="flex items-center gap-2">
                <Award className="h-5 w-5" />
                Overall Performance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="text-center p-4 bg-muted rounded-lg print:border">
                  <p className="text-sm text-muted-foreground">
                    Cumulative Percentage
                  </p>
                  <p className="text-3xl font-bold">
                    {reportCard.cumulative_percentage.toFixed(1)}%
                  </p>
                </div>
                <div className="text-center p-4 bg-muted rounded-lg print:border">
                  <p className="text-sm text-muted-foreground">Overall Grade</p>
                  <div className="mt-2">
                    <Badge
                      variant="outline"
                      className={`text-lg px-4 py-1 ${getGradeColor(
                        reportCard.cumulative_grade
                      )}`}
                    >
                      {reportCard.cumulative_grade || "N/A"}
                    </Badge>
                  </div>
                </div>
                <div className="text-center p-4 bg-muted rounded-lg print:border">
                  <p className="text-sm text-muted-foreground">Performance</p>
                  <p className={`text-xl font-semibold ${performance?.color}`}>
                    {performance?.label || "N/A"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Exam Results */}
        {reportCard.exam_results.length === 0 ? (
          <Card className="print:shadow-none print:border-2 print:mt-4">
            <CardContent className="py-12">
              <div className="text-center">
                <GraduationCap className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">
                  No exam results available for this student
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          reportCard.exam_results.map((examResult) => (
            <Card
              key={examResult.exam_id}
              className="print:shadow-none print:border-2 print:mt-4 print:break-inside-avoid"
            >
              <CardHeader className="print:pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <BookOpen className="h-5 w-5" />
                    {examResult.exam_name}
                  </CardTitle>
                  <Badge variant="secondary">
                    {examTypeLabels[examResult.exam_type] || examResult.exam_type}
                  </Badge>
                </div>
                <CardDescription>
                  Overall: {examResult.overall_percentage.toFixed(1)}% |{" "}
                  Grade: {examResult.overall_grade || "N/A"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Subject</TableHead>
                      <TableHead className="text-center">Code</TableHead>
                      <TableHead className="text-right">Marks</TableHead>
                      <TableHead className="text-right">Max</TableHead>
                      <TableHead className="text-right">%</TableHead>
                      <TableHead className="text-center">Grade</TableHead>
                      <TableHead className="print:hidden">Remarks</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {examResult.subject_grades.map((subjectGrade) => (
                      <TableRow key={subjectGrade.subject_id}>
                        <TableCell className="font-medium">
                          {subjectGrade.subject_name}
                        </TableCell>
                        <TableCell className="text-center">
                          {subjectGrade.subject_code || "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {subjectGrade.marks_obtained}
                        </TableCell>
                        <TableCell className="text-right">
                          {subjectGrade.max_marks}
                        </TableCell>
                        <TableCell className="text-right">
                          {subjectGrade.percentage.toFixed(1)}%
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge
                            variant="outline"
                            className={getGradeColor(subjectGrade.grade)}
                          >
                            {subjectGrade.grade || "-"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground print:hidden">
                          {subjectGrade.remarks || "-"}
                        </TableCell>
                      </TableRow>
                    ))}
                    {/* Total Row */}
                    <TableRow className="font-semibold bg-muted/50">
                      <TableCell>Total</TableCell>
                      <TableCell></TableCell>
                      <TableCell className="text-right">
                        {examResult.total_marks_obtained}
                      </TableCell>
                      <TableCell className="text-right">
                        {examResult.total_max_marks}
                      </TableCell>
                      <TableCell className="text-right">
                        {examResult.overall_percentage.toFixed(1)}%
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge
                          variant="outline"
                          className={getGradeColor(examResult.overall_grade)}
                        >
                          {examResult.overall_grade || "-"}
                        </Badge>
                      </TableCell>
                      <TableCell className="print:hidden"></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ))
        )}

        {/* Grading Scale Reference */}
        <Card className="print:shadow-none print:border-2 print:mt-4">
          <CardHeader className="print:pb-2">
            <CardTitle className="text-sm">Grading Scale</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4 text-sm">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={gradeColors["A+"]}>
                  A+
                </Badge>
                <span>90-100%</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={gradeColors["A"]}>
                  A
                </Badge>
                <span>80-89%</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={gradeColors["B+"]}>
                  B+
                </Badge>
                <span>70-79%</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={gradeColors["B"]}>
                  B
                </Badge>
                <span>60-69%</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={gradeColors["C"]}>
                  C
                </Badge>
                <span>50-59%</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={gradeColors["D"]}>
                  D
                </Badge>
                <span>40-49%</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={gradeColors["F"]}>
                  F
                </Badge>
                <span>Below 40%</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Print Footer */}
        <div className="hidden print:block mt-8 pt-4 border-t text-center text-sm text-muted-foreground">
          <p>
            Generated on {new Date().toLocaleDateString()} | This is a
            computer-generated report card
          </p>
        </div>
      </div>
    </div>
  );
}
