"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Calendar,
  Clock,
  Plus,
  Users,
  GraduationCap,
  BookOpen,
  Filter,
  X,
  Pencil,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import { useConfirmDialog } from "@/components/ConfirmDialog";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
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

interface TeacherItem {
  id: number;
  employee_id: string;
  user: {
    email: string;
    profile_data: Record<string, unknown>;
  } | null;
}

interface SubjectItem {
  id: number;
  name: string;
  code: string;
  credits: number;
  teacher_id: number | null;
  teacher: {
    id: number;
    employee_id: string;
    user: {
      email: string;
      profile_data: Record<string, unknown>;
    } | null;
  } | null;
}

interface ClassListResponse {
  items: ClassItem[];
  total_count: number;
}

interface SectionListResponse {
  items: SectionItem[];
  total_count: number;
}

interface TeacherListResponse {
  items: TeacherItem[];
  total_count: number;
}

interface ConflictCheckResponse {
  has_conflicts: boolean;
  teacher_conflict: {
    id: number;
    class_id: number | null;
    subject_id: number | null;
    teacher_id: number | null;
    day_of_week: number;
    period_number: number;
  } | null;
  class_conflict: {
    id: number;
    class_id: number | null;
    subject_id: number | null;
    teacher_id: number | null;
    day_of_week: number;
    period_number: number;
  } | null;
}

interface TimetableFormData {
  class_id: number;
  section_id: number | null;
  day_of_week: number;
  period_number: number;
  subject_id: number;
  teacher_id: number | null;
  start_time: string;
  end_time: string;
}

const DAYS_OF_WEEK = [
  { value: 0, label: "Monday" },
  { value: 1, label: "Tuesday" },
  { value: 2, label: "Wednesday" },
  { value: 3, label: "Thursday" },
  { value: 4, label: "Friday" },
  { value: 5, label: "Saturday" },
  { value: 6, label: "Sunday" },
];

const PERIODS = [1, 2, 3, 4, 5, 6, 7, 8];

// Manual subjects list as fallback (matching database IDs for Class 1)
const MANUAL_SUBJECTS = [
  { id: 1, name: "Mathematics", code: "MATH1" },
  { id: 2, name: "English", code: "ENG1" },
  { id: 3, name: "Science", code: "SCI1" },
  { id: 4, name: "Social Studies", code: "SOC1" },
  { id: 5, name: "Hindi", code: "HIN1" },
  { id: 6, name: "Computer Science", code: "CS1" },
];

const dayColors: Record<number, string> = {
  0: "bg-blue-50 border-blue-200",
  1: "bg-green-50 border-green-200",
  2: "bg-yellow-50 border-yellow-200",
  3: "bg-purple-50 border-purple-200",
  4: "bg-pink-50 border-pink-200",
  5: "bg-orange-50 border-orange-200",
  6: "bg-gray-50 border-gray-200",
};

export default function TimetablePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { confirm, ConfirmDialog } = useConfirmDialog();

  // View mode state
  const [viewMode, setViewMode] = useState<"class" | "teacher">("class");
  
  // Data state
  const [timetableEntries, setTimetableEntries] = useState<TimetableEntry[]>([]);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [sections, setSections] = useState<SectionItem[]>([]);
  const [teachers, setTeachers] = useState<TeacherItem[]>([]);
  const [subjects, setSubjects] = useState<SubjectItem[]>([]);
  
  // Loading state
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingClasses, setIsLoadingClasses] = useState(true);
  const [isLoadingSections, setIsLoadingSections] = useState(false);
  const [isLoadingTeachers, setIsLoadingTeachers] = useState(true);
  const [isLoadingSubjects, setIsLoadingSubjects] = useState(false);
  const [isLoadingFormSections, setIsLoadingFormSections] = useState(false);
  
  // Selection state
  const [selectedClassId, setSelectedClassId] = useState<string>("");
  const [selectedSectionId, setSelectedSectionId] = useState<string>("");
  const [selectedTeacherId, setSelectedTeacherId] = useState<string>("");

  // Form dialog state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<TimetableEntry | null>(null);
  const [formSections, setFormSections] = useState<SectionItem[]>([]);
  const [formData, setFormData] = useState<TimetableFormData>({
    class_id: 0,
    section_id: null,
    day_of_week: 0,
    period_number: 1,
    subject_id: 0,
    teacher_id: null,
    start_time: "08:00",
    end_time: "08:45",
  });
  const [isSaving, setIsSaving] = useState(false);
  const [conflictWarning, setConflictWarning] = useState<string | null>(null);
  const [isCheckingConflict, setIsCheckingConflict] = useState(false);

  // Check permissions
  const canManageTimetable = user?.role === "admin" || user?.role === "super_admin";

  // Get teacher name helper
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

  // Fetch teachers
  useEffect(() => {
    async function fetchTeachers() {
      try {
        const response = await api.get<TeacherListResponse>("/api/teachers", {
          page_size: 100,
          status: "active",
        });
        setTeachers(response.items);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch teachers");
      } finally {
        setIsLoadingTeachers(false);
      }
    }
    fetchTeachers();
  }, []);

  // Fetch sections when class changes
  useEffect(() => {
    async function fetchSections() {
      if (!selectedClassId) {
        setSections([]);
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
    if (viewMode === "class") {
      fetchSections();
    }
  }, [selectedClassId, viewMode]);

  // Fetch subjects when class changes (for form)
  useEffect(() => {
    async function fetchSubjects() {
      if (!formData.class_id) {
        setSubjects([]);
        return;
      }
      setIsLoadingSubjects(true);
      try {
        const response = await api.get<SubjectItem[]>(`/api/classes/${formData.class_id}/subjects`);
        setSubjects(response);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch subjects");
      } finally {
        setIsLoadingSubjects(false);
      }
    }
    if (isFormOpen && formData.class_id) {
      fetchSubjects();
    }
  }, [formData.class_id, isFormOpen]);

  // Fetch sections for form when class changes
  useEffect(() => {
    async function fetchFormSections() {
      if (!formData.class_id) {
        setFormSections([]);
        return;
      }
      setIsLoadingFormSections(true);
      try {
        const response = await api.get<SectionListResponse>("/api/sections", {
          class_id: formData.class_id,
          page_size: 100,
        });
        setFormSections(response.items);
      } catch (err) {
        const apiError = err as ApiError;
        console.error("Failed to fetch sections for form:", apiError);
      } finally {
        setIsLoadingFormSections(false);
      }
    }
    if (isFormOpen && formData.class_id) {
      fetchFormSections();
    }
  }, [formData.class_id, isFormOpen]);

  // Fetch timetable entries
  useEffect(() => {
    async function fetchTimetable() {
      if (viewMode === "class" && !selectedClassId) {
        setTimetableEntries([]);
        setIsLoading(false);
        return;
      }
      if (viewMode === "teacher" && !selectedTeacherId) {
        setTimetableEntries([]);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        let response;
        if (viewMode === "class") {
          response = await api.get<{ entries: TimetableEntry[] }>(
            `/api/timetable/class/${selectedClassId}`,
            selectedSectionId ? { section_id: parseInt(selectedSectionId) } : {}
          );
        } else {
          response = await api.get<{ entries: TimetableEntry[] }>(
            `/api/timetable/teacher/${selectedTeacherId}`
          );
        }
        setTimetableEntries(response.entries);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch timetable");
      } finally {
        setIsLoading(false);
      }
    }
    fetchTimetable();
  }, [viewMode, selectedClassId, selectedSectionId, selectedTeacherId]);

  // Check for conflicts
  const checkConflicts = useCallback(async () => {
    if (!formData.class_id || !formData.subject_id) {
      setConflictWarning(null);
      return;
    }

    setIsCheckingConflict(true);
    try {
      const params: Record<string, string | number> = {
        class_id: formData.class_id,
        day_of_week: formData.day_of_week,
        period_number: formData.period_number,
        start_time: formData.start_time,
        end_time: formData.end_time,
      };
      if (formData.teacher_id) {
        params.teacher_id = formData.teacher_id;
      }
      if (formData.section_id) {
        params.section_id = formData.section_id;
      }
      if (editingEntry) {
        params.exclude_id = editingEntry.id;
      }

      const response = await api.get<ConflictCheckResponse>("/api/timetable/check-conflicts", params);
      
      if (response.has_conflicts) {
        const warnings: string[] = [];
        if (response.teacher_conflict) {
          warnings.push("Teacher is already assigned to another class at this time");
        }
        if (response.class_conflict) {
          warnings.push("This class already has a period scheduled at this time");
        }
        setConflictWarning(warnings.join(". "));
      } else {
        setConflictWarning(null);
      }
    } catch (err) {
      // Silently ignore conflict check errors
      setConflictWarning(null);
    } finally {
      setIsCheckingConflict(false);
    }
  }, [formData, editingEntry]);

  // Check conflicts when form data changes
  useEffect(() => {
    const timer = setTimeout(() => {
      if (isFormOpen) {
        checkConflicts();
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [formData.day_of_week, formData.period_number, formData.teacher_id, formData.start_time, formData.end_time, isFormOpen, checkConflicts]);

  // Open form for new entry
  const handleAddEntry = () => {
    setEditingEntry(null);
    setFormData({
      class_id: selectedClassId ? parseInt(selectedClassId) : 0,
      section_id: selectedSectionId ? parseInt(selectedSectionId) : null,
      day_of_week: 0,
      period_number: 1,
      subject_id: 0,
      teacher_id: null,
      start_time: "08:00",
      end_time: "08:45",
    });
    setConflictWarning(null);
    setIsFormOpen(true);
  };

  // Open form for editing
  const handleEditEntry = (entry: TimetableEntry) => {
    setEditingEntry(entry);
    setFormData({
      class_id: entry.class_id,
      section_id: entry.section_id,
      day_of_week: entry.day_of_week,
      period_number: entry.period_number,
      subject_id: entry.subject_id,
      teacher_id: entry.teacher_id,
      start_time: entry.start_time,
      end_time: entry.end_time,
    });
    setConflictWarning(null);
    setIsFormOpen(true);
  };

  // Save timetable entry
  const handleSave = async () => {
    if (!formData.class_id || !formData.subject_id) {
      toast.error("Please fill in all required fields");
      return;
    }

    setIsSaving(true);
    try {
      const payload = {
        class_id: formData.class_id,
        section_id: formData.section_id,
        day_of_week: formData.day_of_week,
        period_number: formData.period_number,
        subject_id: formData.subject_id,
        teacher_id: formData.teacher_id,
        start_time: formData.start_time,
        end_time: formData.end_time,
      };

      if (editingEntry) {
        await api.put(`/api/timetable/${editingEntry.id}`, payload);
        toast.success("Timetable entry updated successfully");
      } else {
        await api.post("/api/timetable", payload);
        toast.success("Timetable entry created successfully");
      }

      setIsFormOpen(false);
      // Refresh timetable
      if (viewMode === "class" && selectedClassId) {
        const response = await api.get<{ entries: TimetableEntry[] }>(
          `/api/timetable/class/${selectedClassId}`,
          selectedSectionId ? { section_id: parseInt(selectedSectionId) } : {}
        );
        setTimetableEntries(response.entries);
      } else if (viewMode === "teacher" && selectedTeacherId) {
        const response = await api.get<{ entries: TimetableEntry[] }>(
          `/api/timetable/teacher/${selectedTeacherId}`
        );
        setTimetableEntries(response.entries);
      }
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to save timetable entry");
    } finally {
      setIsSaving(false);
    }
  };

  // Delete timetable entry
  const handleDelete = (entry: TimetableEntry) => {
    confirm({
      title: "Delete Timetable Entry",
      description: `Are you sure you want to delete this timetable entry for ${entry.subject_name || "Unknown Subject"} on ${entry.day_name}?`,
      confirmLabel: "Delete",
      variant: "destructive",
      onConfirm: async () => {
        try {
          await api.delete(`/api/timetable/${entry.id}`);
          toast.success("Timetable entry deleted successfully");
          setTimetableEntries((prev) => prev.filter((e) => e.id !== entry.id));
        } catch (err) {
          const apiError = err as ApiError;
          toast.error(apiError.message || "Failed to delete timetable entry");
        }
      },
    });
  };

  // Get entry for a specific day and period
  const getEntryForSlot = (dayOfWeek: number, periodNumber: number): TimetableEntry | undefined => {
    return timetableEntries.find(
      (entry) => entry.day_of_week === dayOfWeek && entry.period_number === periodNumber
    );
  };

  // Render timetable grid
  const renderTimetableGrid = () => {
    const activeDays = DAYS_OF_WEEK.filter((day) => day.value <= 5); // Monday to Saturday

    return (
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="border p-2 bg-muted text-left w-20">Period</th>
              {activeDays.map((day) => (
                <th key={day.value} className="border p-2 bg-muted text-center min-w-[140px]">
                  {day.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PERIODS.map((period) => (
              <tr key={period}>
                <td className="border p-2 bg-muted font-medium text-center">
                  {period}
                </td>
                {activeDays.map((day) => {
                  const entry = getEntryForSlot(day.value, period);
                  return (
                    <td
                      key={`${day.value}-${period}`}
                      className={`border p-1 ${entry ? dayColors[day.value] : "bg-white"}`}
                    >
                      {entry ? (
                        <div className="p-2 rounded text-sm group relative">
                          <div className="font-medium text-[#21808D]">
                            {entry.subject_name || entry.subject_code || "Unknown"}
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            {entry.teacher_name || "No teacher"}
                          </div>
                          <div className="text-xs text-gray-500">
                            {entry.start_time} - {entry.end_time}
                          </div>
                          {viewMode === "teacher" && entry.class_name && (
                            <div className="text-xs text-gray-500 mt-1">
                              {entry.class_name}
                              {entry.section_name && ` - ${entry.section_name}`}
                            </div>
                          )}
                          {canManageTimetable && (
                            <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => handleEditEntry(entry)}
                                className="h-6 w-6"
                              >
                                <Pencil className="h-3 w-3" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => handleDelete(entry)}
                                className="h-6 w-6 text-destructive"
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="h-16 flex items-center justify-center text-gray-400 text-sm">
                          {canManageTimetable && viewMode === "class" && selectedClassId && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="opacity-0 hover:opacity-100 transition-opacity"
                              onClick={() => {
                                setEditingEntry(null);
                                setFormData({
                                  class_id: parseInt(selectedClassId),
                                  section_id: selectedSectionId ? parseInt(selectedSectionId) : null,
                                  day_of_week: day.value,
                                  period_number: period,
                                  subject_id: 0,
                                  teacher_id: null,
                                  start_time: "08:00",
                                  end_time: "08:45",
                                });
                                setConflictWarning(null);
                                setIsFormOpen(true);
                              }}
                            >
                              <Plus className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <ConfirmDialog />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Timetable</h1>
          <p className="text-muted-foreground">
            View and manage class and teacher schedules
          </p>
        </div>
        {canManageTimetable && viewMode === "class" && selectedClassId && (
          <Button onClick={handleAddEntry}>
            <Plus className="h-4 w-4 mr-2" />
            Add Entry
          </Button>
        )}
      </div>

      {/* View Mode Toggle */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end">
            {/* View Mode Selector */}
            <div>
              <label className="text-sm font-medium mb-2 block">View Mode</label>
              <div className="flex gap-2">
                <Button
                  variant={viewMode === "class" ? "default" : "outline"}
                  onClick={() => {
                    setViewMode("class");
                    setSelectedTeacherId("");
                  }}
                >
                  <Users className="h-4 w-4 mr-2" />
                  Class-wise
                </Button>
                <Button
                  variant={viewMode === "teacher" ? "default" : "outline"}
                  onClick={() => {
                    setViewMode("teacher");
                    setSelectedClassId("");
                    setSelectedSectionId("");
                  }}
                >
                  <GraduationCap className="h-4 w-4 mr-2" />
                  Teacher-wise
                </Button>
              </div>
            </div>

            {/* Class/Teacher Selection */}
            {viewMode === "class" ? (
              <>
                <div className="flex-1 max-w-xs">
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
                <div className="flex-1 max-w-xs">
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
              </>
            ) : (
              <div className="flex-1 max-w-xs">
                <label className="text-sm font-medium mb-2 block">Teacher</label>
                {isLoadingTeachers ? (
                  <Skeleton className="h-9 w-full" />
                ) : (
                  <select
                    value={selectedTeacherId}
                    onChange={(e) => setSelectedTeacherId(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">Select Teacher</option>
                    {teachers.map((teacher) => (
                      <option key={teacher.id} value={teacher.id}>
                        {getTeacherName(teacher)}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Timetable Grid */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            {viewMode === "class" ? "Class Timetable" : "Teacher Schedule"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {(viewMode === "class" && !selectedClassId) || (viewMode === "teacher" && !selectedTeacherId) ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                Please select a {viewMode === "class" ? "class" : "teacher"} to view the timetable
              </p>
            </div>
          ) : isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : timetableEntries.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                No timetable entries found
              </p>
              {canManageTimetable && viewMode === "class" && (
                <Button variant="link" onClick={handleAddEntry} className="mt-2">
                  Add your first entry
                </Button>
              )}
            </div>
          ) : (
            renderTimetableGrid()
          )}
        </CardContent>
      </Card>

      {/* Entry Form Dialog */}
      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingEntry ? "Edit Timetable Entry" : "Add Timetable Entry"}
            </DialogTitle>
            <DialogDescription>
              {editingEntry
                ? "Update the timetable entry details"
                : "Create a new timetable entry"}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Class Selection */}
            <div>
              <label className="text-sm font-medium mb-2 block">Class *</label>
              <select
                value={formData.class_id || ""}
                onChange={(e) => {
                  const classId = parseInt(e.target.value) || 0;
                  setFormData((prev) => ({
                    ...prev,
                    class_id: classId,
                    subject_id: 0,
                  }));
                }}
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                disabled={!!editingEntry}
              >
                <option value="">Select Class</option>
                {classes.map((cls) => (
                  <option key={cls.id} value={cls.id}>
                    {cls.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Section Selection */}
            <div>
              <label className="text-sm font-medium mb-2 block">Section</label>
              {isLoadingFormSections ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <select
                  value={formData.section_id || ""}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      section_id: e.target.value ? parseInt(e.target.value) : null,
                    }))
                  }
                  className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  disabled={!formData.class_id}
                >
                  <option value="">All Sections</option>
                  {formSections.map((section) => (
                    <option key={section.id} value={section.id}>
                      {section.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Day and Period */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Day *</label>
                <select
                  value={formData.day_of_week}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      day_of_week: parseInt(e.target.value),
                    }))
                  }
                  className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                >
                  {DAYS_OF_WEEK.map((day) => (
                    <option key={day.value} value={day.value}>
                      {day.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Period *</label>
                <select
                  value={formData.period_number}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      period_number: parseInt(e.target.value),
                    }))
                  }
                  className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                >
                  {PERIODS.map((period) => (
                    <option key={period} value={period}>
                      Period {period}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Subject Selection */}
            <div>
              <label className="text-sm font-medium mb-2 block">Subject *</label>
              {isLoadingSubjects ? (
                <Skeleton className="h-9 w-full" />
              ) : (
                <select
                  value={formData.subject_id || ""}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      subject_id: parseInt(e.target.value) || 0,
                    }))
                  }
                  className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  disabled={!formData.class_id}
                >
                  <option value="">Select Subject</option>
                  {subjects.length > 0
                    ? subjects.map((subject) => (
                        <option key={subject.id} value={subject.id}>
                          {subject.name} ({subject.code})
                        </option>
                      ))
                    : MANUAL_SUBJECTS.map((subject) => (
                        <option key={subject.id} value={subject.id}>
                          {subject.name} ({subject.code})
                        </option>
                      ))}
                </select>
              )}
            </div>

            {/* Teacher Selection */}
            <div>
              <label className="text-sm font-medium mb-2 block">Teacher</label>
              <select
                value={formData.teacher_id || ""}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    teacher_id: e.target.value ? parseInt(e.target.value) : null,
                  }))
                }
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
              >
                <option value="">Select Teacher</option>
                {teachers.map((teacher) => (
                  <option key={teacher.id} value={teacher.id}>
                    {getTeacherName(teacher)}
                  </option>
                ))}
              </select>
            </div>

            {/* Time Selection */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Start Time *</label>
                <Input
                  type="time"
                  value={formData.start_time}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      start_time: e.target.value,
                    }))
                  }
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">End Time *</label>
                <Input
                  type="time"
                  value={formData.end_time}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      end_time: e.target.value,
                    }))
                  }
                />
              </div>
            </div>

            {/* Conflict Warning */}
            {conflictWarning && (
              <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-800">
                  <p className="font-medium">Potential Conflict Detected</p>
                  <p>{conflictWarning}</p>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsFormOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={isSaving || !formData.class_id || !formData.subject_id}
            >
              {isSaving ? "Saving..." : editingEntry ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
