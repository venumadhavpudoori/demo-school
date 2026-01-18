"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Pencil,
  Trash2,
  Mail,
  Phone,
  MapPin,
  Calendar,
  GraduationCap,
  User,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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
interface UserResponse {
  id: number;
  email: string;
  profile_data: Record<string, unknown>;
  is_active: boolean;
}

interface StudentInfo {
  id: number;
  admission_number: string;
  class_id: number | null;
  class_name: string | null;
  section_id: number | null;
  section_name: string | null;
  roll_number: number | null;
  date_of_birth: string;
  gender: string;
  address: string | null;
  admission_date: string;
  status: string;
  user: UserResponse;
}

interface AttendanceSummary {
  total_days: number;
  present_days: number;
  absent_days: number;
  late_days: number;
  half_days: number;
  attendance_percentage: number;
}

interface GradeItem {
  id: number;
  subject_name: string | null;
  exam_name: string | null;
  marks_obtained: number;
  max_marks: number;
  percentage: number;
  grade: string | null;
  remarks: string | null;
}

interface FeeItem {
  id: number;
  fee_type: string;
  amount: number;
  paid_amount: number;
  due_date: string;
  status: string;
}

interface FeesSummary {
  total_amount: number;
  total_paid: number;
  balance: number;
  pending_count: number;
  recent_fees: FeeItem[];
}

interface StudentProfileResponse {
  student: StudentInfo;
  attendance: AttendanceSummary;
  grades: GradeItem[];
  fees: FeesSummary;
}

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-gray-100 text-gray-800",
  graduated: "bg-blue-100 text-blue-800",
  transferred: "bg-yellow-100 text-yellow-800",
  deleted: "bg-red-100 text-red-800",
};

const feeStatusColors: Record<string, string> = {
  paid: "bg-green-100 text-green-800",
  partial: "bg-yellow-100 text-yellow-800",
  pending: "bg-red-100 text-red-800",
  overdue: "bg-red-200 text-red-900",
};

export default function StudentProfilePage() {
  const router = useRouter();
  const params = useParams();
  const studentId = params.id as string;
  const { user } = useAuth();
  const { confirm, ConfirmDialog } = useConfirmDialog();

  const [isLoading, setIsLoading] = useState(true);
  const [profile, setProfile] = useState<StudentProfileResponse | null>(null);

  // Check permissions
  const canManageStudents = user?.role === "admin" || user?.role === "super_admin";
  const canEditStudents = canManageStudents || user?.role === "teacher";

  // Fetch student profile
  useEffect(() => {
    async function fetchProfile() {
      try {
        const response = await api.get<StudentProfileResponse>(
          `/api/students/${studentId}/profile`
        );
        setProfile(response);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch student profile");
        router.push("/dashboard/students");
      } finally {
        setIsLoading(false);
      }
    }
    fetchProfile();
  }, [studentId, router]);

  // Handle delete
  const handleDelete = () => {
    if (!profile) return;

    const studentName =
      profile.student.user?.profile_data?.first_name ||
      profile.student.user?.email ||
      profile.student.admission_number;

    confirm({
      title: "Delete Student",
      description: `Are you sure you want to delete ${studentName}? This action will soft-delete the student record.`,
      confirmLabel: "Delete",
      variant: "destructive",
      onConfirm: async () => {
        try {
          await api.delete(`/api/students/${studentId}`);
          toast.success("Student deleted successfully");
          router.push("/dashboard/students");
        } catch (err) {
          const apiError = err as ApiError;
          toast.error(apiError.message || "Failed to delete student");
        }
      },
    });
  };

  // Get student display name
  const getStudentName = () => {
    if (!profile) return "";
    const firstName = profile.student.user?.profile_data?.first_name as string;
    const lastName = profile.student.user?.profile_data?.last_name as string;
    if (firstName || lastName) {
      return `${firstName || ""} ${lastName || ""}`.trim();
    }
    return profile.student.user?.email || profile.student.admission_number;
  };

  // Format date
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount);
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
        <div className="grid gap-6 md:grid-cols-3">
          <Skeleton className="h-48" />
          <Skeleton className="h-48 md:col-span-2" />
        </div>
      </div>
    );
  }

  if (!profile) {
    return null;
  }

  return (
    <div className="space-y-6">
      <ConfirmDialog />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/students">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{getStudentName()}</h1>
              <Badge
                variant="secondary"
                className={statusColors[profile.student.status] || ""}
              >
                {profile.student.status}
              </Badge>
            </div>
            <p className="text-muted-foreground">
              {profile.student.admission_number}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {canEditStudents && (
            <Link href={`/dashboard/students/${studentId}/edit`}>
              <Button variant="outline">
                <Pencil className="h-4 w-4 mr-2" />
                Edit
              </Button>
            </Link>
          )}
          {canManageStudents && (
            <Button variant="destructive" onClick={handleDelete}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Attendance</p>
                <p className="text-2xl font-bold">
                  {profile.attendance.attendance_percentage.toFixed(1)}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-blue-100 rounded-lg">
                <GraduationCap className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Grades</p>
                <p className="text-2xl font-bold">{profile.grades.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <AlertCircle className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Pending Fees</p>
                <p className="text-2xl font-bold">{profile.fees.pending_count}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Calendar className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Present Days</p>
                <p className="text-2xl font-bold">
                  {profile.attendance.present_days}/{profile.attendance.total_days}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="info" className="space-y-4">
        <TabsList>
          <TabsTrigger value="info">Information</TabsTrigger>
          <TabsTrigger value="attendance">Attendance</TabsTrigger>
          <TabsTrigger value="grades">Grades</TabsTrigger>
          <TabsTrigger value="fees">Fees</TabsTrigger>
        </TabsList>

        {/* Information Tab */}
        <TabsContent value="info" className="space-y-4">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Personal Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Personal Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Email</p>
                    <p>{profile.student.user?.email}</p>
                  </div>
                </div>
                {profile.student.user?.profile_data?.phone ? (
                  <div className="flex items-center gap-3">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm text-muted-foreground">Phone</p>
                      <p>{String(profile.student.user.profile_data.phone)}</p>
                    </div>
                  </div>
                ) : null}
                <div className="flex items-center gap-3">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Date of Birth</p>
                    <p>{formatDate(profile.student.date_of_birth)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Gender</p>
                    <p className="capitalize">{profile.student.gender}</p>
                  </div>
                </div>
                {profile.student.address && (
                  <div className="flex items-center gap-3">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm text-muted-foreground">Address</p>
                      <p>{profile.student.address}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Academic Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GraduationCap className="h-5 w-5" />
                  Academic Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Admission Number</p>
                  <p className="font-medium">{profile.student.admission_number}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Admission Date</p>
                  <p>{formatDate(profile.student.admission_date)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Class</p>
                  <p>{profile.student.class_name || "Not assigned"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Section</p>
                  <p>{profile.student.section_name || "Not assigned"}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Roll Number</p>
                  <p>{profile.student.roll_number || "Not assigned"}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Attendance Tab */}
        <TabsContent value="attendance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Attendance Summary</CardTitle>
              <CardDescription>
                Overview of attendance for the current academic period
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-5">
                <div className="text-center p-4 bg-muted rounded-lg">
                  <p className="text-3xl font-bold">{profile.attendance.total_days}</p>
                  <p className="text-sm text-muted-foreground">Total Days</p>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="flex items-center justify-center gap-2">
                    <CheckCircle className="h-5 w-5 text-green-600" />
                    <p className="text-3xl font-bold text-green-600">
                      {profile.attendance.present_days}
                    </p>
                  </div>
                  <p className="text-sm text-muted-foreground">Present</p>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="flex items-center justify-center gap-2">
                    <XCircle className="h-5 w-5 text-red-600" />
                    <p className="text-3xl font-bold text-red-600">
                      {profile.attendance.absent_days}
                    </p>
                  </div>
                  <p className="text-sm text-muted-foreground">Absent</p>
                </div>
                <div className="text-center p-4 bg-yellow-50 rounded-lg">
                  <div className="flex items-center justify-center gap-2">
                    <Clock className="h-5 w-5 text-yellow-600" />
                    <p className="text-3xl font-bold text-yellow-600">
                      {profile.attendance.late_days}
                    </p>
                  </div>
                  <p className="text-sm text-muted-foreground">Late</p>
                </div>
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <div className="flex items-center justify-center gap-2">
                    <AlertCircle className="h-5 w-5 text-orange-600" />
                    <p className="text-3xl font-bold text-orange-600">
                      {profile.attendance.half_days}
                    </p>
                  </div>
                  <p className="text-sm text-muted-foreground">Half Days</p>
                </div>
              </div>
              <div className="mt-6 p-4 bg-muted rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Attendance Percentage</span>
                  <span className="text-2xl font-bold">
                    {profile.attendance.attendance_percentage.toFixed(1)}%
                  </span>
                </div>
                <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500 rounded-full"
                    style={{ width: `${profile.attendance.attendance_percentage}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Grades Tab */}
        <TabsContent value="grades" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Academic Performance</CardTitle>
              <CardDescription>
                Grades and exam results
              </CardDescription>
            </CardHeader>
            <CardContent>
              {profile.grades.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">No grades recorded yet</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Subject</TableHead>
                      <TableHead>Exam</TableHead>
                      <TableHead className="text-right">Marks</TableHead>
                      <TableHead className="text-right">Percentage</TableHead>
                      <TableHead>Grade</TableHead>
                      <TableHead>Remarks</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {profile.grades.map((grade) => (
                      <TableRow key={grade.id}>
                        <TableCell className="font-medium">
                          {grade.subject_name || "-"}
                        </TableCell>
                        <TableCell>{grade.exam_name || "-"}</TableCell>
                        <TableCell className="text-right">
                          {grade.marks_obtained}/{grade.max_marks}
                        </TableCell>
                        <TableCell className="text-right">
                          {grade.percentage.toFixed(1)}%
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{grade.grade || "-"}</Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {grade.remarks || "-"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Fees Tab */}
        <TabsContent value="fees" className="space-y-4">
          {/* Fee Summary */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Total Amount</p>
                <p className="text-2xl font-bold">
                  {formatCurrency(profile.fees.total_amount)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Total Paid</p>
                <p className="text-2xl font-bold text-green-600">
                  {formatCurrency(profile.fees.total_paid)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Balance</p>
                <p className="text-2xl font-bold text-red-600">
                  {formatCurrency(profile.fees.balance)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Pending Fees</p>
                <p className="text-2xl font-bold">{profile.fees.pending_count}</p>
              </CardContent>
            </Card>
          </div>

          {/* Recent Fees */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Fees</CardTitle>
              <CardDescription>
                Latest fee records and payment status
              </CardDescription>
            </CardHeader>
            <CardContent>
              {profile.fees.recent_fees.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">No fee records found</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Fee Type</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead className="text-right">Paid</TableHead>
                      <TableHead>Due Date</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {profile.fees.recent_fees.map((fee) => (
                      <TableRow key={fee.id}>
                        <TableCell className="font-medium">{fee.fee_type}</TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(fee.amount)}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(fee.paid_amount)}
                        </TableCell>
                        <TableCell>{formatDate(fee.due_date)}</TableCell>
                        <TableCell>
                          <Badge
                            variant="secondary"
                            className={feeStatusColors[fee.status] || ""}
                          >
                            {fee.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
