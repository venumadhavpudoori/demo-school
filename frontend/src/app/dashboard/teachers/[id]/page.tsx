"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Pencil,
  Mail,
  Phone,
  Calendar,
  GraduationCap,
  User,
  BookOpen,
  Clock,
  Users,
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
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
interface UserResponse {
  id: number;
  email: string;
  profile_data: Record<string, unknown>;
  is_active: boolean;
}

interface TeacherResponse {
  id: number;
  employee_id: string;
  subjects: string[] | null;
  classes_assigned: number[] | null;
  qualifications: string | null;
  joining_date: string;
  status: string;
  user: UserResponse | null;
  created_at: string;
  updated_at: string;
}

interface ClassInfo {
  id: number;
  name: string;
  grade_level: number;
  academic_year: string;
  is_class_teacher: boolean;
}


interface TeacherClassesResponse {
  teacher_id: number;
  assigned_classes: ClassInfo[];
  class_teacher_of: ClassInfo[];
}

interface TimetableEntry {
  id: number;
  class_id: number;
  class_name: string | null;
  section_id: number | null;
  section_name: string | null;
  day_of_week: number;
  day_name: string;
  period_number: number;
  subject_id: number;
  subject_name: string | null;
  subject_code: string | null;
  teacher_id: number | null;
  teacher_name: string | null;
  start_time: string;
  end_time: string;
}

interface TeacherTimetableResponse {
  teacher_id: number;
  entries: TimetableEntry[];
}

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-gray-100 text-gray-800",
  on_leave: "bg-yellow-100 text-yellow-800",
  resigned: "bg-red-100 text-red-800",
};

const dayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function TeacherProfilePage() {
  const router = useRouter();
  const params = useParams();
  const teacherId = params.id as string;
  const { user } = useAuth();

  const [isLoading, setIsLoading] = useState(true);
  const [teacher, setTeacher] = useState<TeacherResponse | null>(null);
  const [classes, setClasses] = useState<TeacherClassesResponse | null>(null);
  const [timetable, setTimetable] = useState<TeacherTimetableResponse | null>(null);

  // Check permissions
  const canManageTeachers = user?.role === "admin" || user?.role === "super_admin";


  // Fetch teacher data
  useEffect(() => {
    async function fetchTeacherData() {
      try {
        // Fetch teacher details, classes, and timetable in parallel
        const [teacherData, classesData, timetableData] = await Promise.all([
          api.get<TeacherResponse>(`/api/teachers/${teacherId}`),
          api.get<TeacherClassesResponse>(`/api/teachers/${teacherId}/classes`),
          api.get<TeacherTimetableResponse>(`/api/timetable/teacher/${teacherId}`),
        ]);

        setTeacher(teacherData);
        setClasses(classesData);
        setTimetable(timetableData);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch teacher profile");
        router.push("/dashboard/teachers");
      } finally {
        setIsLoading(false);
      }
    }
    fetchTeacherData();
  }, [teacherId, router]);

  // Get teacher display name
  const getTeacherName = () => {
    if (!teacher) return "";
    const firstName = teacher.user?.profile_data?.first_name as string;
    const lastName = teacher.user?.profile_data?.last_name as string;
    if (firstName || lastName) {
      return `${firstName || ""} ${lastName || ""}`.trim();
    }
    return teacher.user?.email || teacher.employee_id;
  };

  // Format date
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  // Format time
  const formatTime = (timeStr: string) => {
    // Handle time strings like "08:00:00" or "08:00"
    const [hours, minutes] = timeStr.split(":");
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? "PM" : "AM";
    const hour12 = hour % 12 || 12;
    return `${hour12}:${minutes} ${ampm}`;
  };


  // Group timetable entries by day
  const getTimetableByDay = () => {
    if (!timetable) return {};
    const byDay: Record<number, TimetableEntry[]> = {};
    timetable.entries.forEach((entry) => {
      if (!byDay[entry.day_of_week]) {
        byDay[entry.day_of_week] = [];
      }
      byDay[entry.day_of_week].push(entry);
    });
    // Sort entries within each day by period number
    Object.keys(byDay).forEach((day) => {
      byDay[parseInt(day)].sort((a, b) => a.period_number - b.period_number);
    });
    return byDay;
  };

  // Get total classes count
  const getTotalClassesCount = () => {
    if (!classes) return 0;
    const assignedIds = new Set(classes.assigned_classes.map((c) => c.id));
    const classTeacherIds = new Set(classes.class_teacher_of.map((c) => c.id));
    return new Set([...assignedIds, ...classTeacherIds]).size;
  };

  // Get total periods per week
  const getTotalPeriodsPerWeek = () => {
    if (!timetable) return 0;
    return timetable.entries.length;
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

  if (!teacher) {
    return null;
  }

  const timetableByDay = getTimetableByDay();


  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/teachers">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{getTeacherName()}</h1>
              <Badge
                variant="secondary"
                className={statusColors[teacher.status] || ""}
              >
                {teacher.status.replace("_", " ")}
              </Badge>
            </div>
            <p className="text-muted-foreground">{teacher.employee_id}</p>
          </div>
        </div>
        {canManageTeachers && (
          <Link href={`/dashboard/teachers/${teacherId}/edit`}>
            <Button variant="outline">
              <Pencil className="h-4 w-4 mr-2" />
              Edit
            </Button>
          </Link>
        )}
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-blue-100 rounded-lg">
                <BookOpen className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Subjects</p>
                <p className="text-2xl font-bold">
                  {teacher.subjects?.length || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-green-100 rounded-lg">
                <Users className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Classes</p>
                <p className="text-2xl font-bold">{getTotalClassesCount()}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Clock className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Periods/Week</p>
                <p className="text-2xl font-bold">{getTotalPeriodsPerWeek()}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <GraduationCap className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Class Teacher</p>
                <p className="text-2xl font-bold">
                  {classes?.class_teacher_of.length || 0}
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
          <TabsTrigger value="classes">Classes</TabsTrigger>
          <TabsTrigger value="schedule">Schedule</TabsTrigger>
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
                    <p>{teacher.user?.email}</p>
                  </div>
                </div>
                {teacher.user?.profile_data?.phone ? (
                  <div className="flex items-center gap-3">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm text-muted-foreground">Phone</p>
                      <p>{String(teacher.user.profile_data.phone)}</p>
                    </div>
                  </div>
                ) : null}
                <div className="flex items-center gap-3">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Joining Date</p>
                    <p>{formatDate(teacher.joining_date)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Status</p>
                    <Badge
                      variant="secondary"
                      className={statusColors[teacher.status] || ""}
                    >
                      {teacher.status.replace("_", " ")}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Professional Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GraduationCap className="h-5 w-5" />
                  Professional Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Employee ID</p>
                  <p className="font-medium">{teacher.employee_id}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Subjects</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {teacher.subjects && teacher.subjects.length > 0 ? (
                      teacher.subjects.map((subject, idx) => (
                        <Badge key={idx} variant="outline">
                          {subject}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-muted-foreground">No subjects assigned</span>
                    )}
                  </div>
                </div>
                {teacher.qualifications && (
                  <div>
                    <p className="text-sm text-muted-foreground">Qualifications</p>
                    <p className="whitespace-pre-wrap">{teacher.qualifications}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>


        {/* Classes Tab */}
        <TabsContent value="classes" className="space-y-4">
          {/* Class Teacher Of */}
          {classes && classes.class_teacher_of.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Class Teacher Of</CardTitle>
                <CardDescription>
                  Classes where this teacher is the class teacher
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Class Name</TableHead>
                      <TableHead>Grade Level</TableHead>
                      <TableHead>Academic Year</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {classes.class_teacher_of.map((cls) => (
                      <TableRow key={cls.id}>
                        <TableCell className="font-medium">{cls.name}</TableCell>
                        <TableCell>Grade {cls.grade_level}</TableCell>
                        <TableCell>{cls.academic_year}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {/* Assigned Classes */}
          <Card>
            <CardHeader>
              <CardTitle>Assigned Classes</CardTitle>
              <CardDescription>
                Classes where this teacher teaches
              </CardDescription>
            </CardHeader>
            <CardContent>
              {classes && classes.assigned_classes.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Class Name</TableHead>
                      <TableHead>Grade Level</TableHead>
                      <TableHead>Academic Year</TableHead>
                      <TableHead>Role</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {classes.assigned_classes.map((cls) => (
                      <TableRow key={cls.id}>
                        <TableCell className="font-medium">{cls.name}</TableCell>
                        <TableCell>Grade {cls.grade_level}</TableCell>
                        <TableCell>{cls.academic_year}</TableCell>
                        <TableCell>
                          {cls.is_class_teacher ? (
                            <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                              Class Teacher
                            </Badge>
                          ) : (
                            <Badge variant="outline">Subject Teacher</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">No classes assigned yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>


        {/* Schedule Tab */}
        <TabsContent value="schedule" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Weekly Schedule</CardTitle>
              <CardDescription>
                Teaching schedule for the week
              </CardDescription>
            </CardHeader>
            <CardContent>
              {timetable && timetable.entries.length > 0 ? (
                <div className="space-y-6">
                  {dayNames.map((dayName, dayIndex) => {
                    const dayEntries = timetableByDay[dayIndex];
                    if (!dayEntries || dayEntries.length === 0) return null;

                    return (
                      <div key={dayIndex}>
                        <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
                          <Calendar className="h-4 w-4" />
                          {dayName}
                        </h3>
                        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                          {dayEntries.map((entry) => (
                            <Card key={entry.id} className="bg-muted/50">
                              <CardContent className="pt-4">
                                <div className="flex justify-between items-start mb-2">
                                  <Badge variant="outline">
                                    Period {entry.period_number}
                                  </Badge>
                                  <span className="text-sm text-muted-foreground">
                                    {formatTime(entry.start_time)} - {formatTime(entry.end_time)}
                                  </span>
                                </div>
                                <p className="font-medium">
                                  {entry.subject_name || "Unknown Subject"}
                                  {entry.subject_code && (
                                    <span className="text-muted-foreground ml-1">
                                      ({entry.subject_code})
                                    </span>
                                  )}
                                </p>
                                <p className="text-sm text-muted-foreground">
                                  {entry.class_name || "Unknown Class"}
                                  {entry.section_name && ` - ${entry.section_name}`}
                                </p>
                              </CardContent>
                            </Card>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No schedule entries found</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    The timetable for this teacher has not been set up yet.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Schedule Summary Table */}
          {timetable && timetable.entries.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Schedule Summary</CardTitle>
                <CardDescription>
                  All periods in a tabular format
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Day</TableHead>
                      <TableHead>Period</TableHead>
                      <TableHead>Time</TableHead>
                      <TableHead>Subject</TableHead>
                      <TableHead>Class</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {timetable.entries
                      .sort((a, b) => {
                        if (a.day_of_week !== b.day_of_week) {
                          return a.day_of_week - b.day_of_week;
                        }
                        return a.period_number - b.period_number;
                      })
                      .map((entry) => (
                        <TableRow key={entry.id}>
                          <TableCell className="font-medium">
                            {entry.day_name}
                          </TableCell>
                          <TableCell>Period {entry.period_number}</TableCell>
                          <TableCell>
                            {formatTime(entry.start_time)} - {formatTime(entry.end_time)}
                          </TableCell>
                          <TableCell>
                            {entry.subject_name || "-"}
                            {entry.subject_code && (
                              <span className="text-muted-foreground ml-1">
                                ({entry.subject_code})
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            {entry.class_name || "-"}
                            {entry.section_name && ` - ${entry.section_name}`}
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
