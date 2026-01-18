"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Plus,
  ChevronLeft,
  ChevronRight,
  Eye,
  Edit,
  Trash2,
  Filter,
  X,
  Megaphone,
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
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
interface AuthorInfo {
  id: number;
  email: string;
  profile_data: {
    first_name?: string;
    last_name?: string;
  };
}

interface AnnouncementListItem {
  id: number;
  title: string;
  content: string;
  target_audience: string;
  created_by: number | null;
  author: AuthorInfo | null;
  created_at: string | null;
}

interface AnnouncementListResponse {
  items: AnnouncementListItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

const audienceColors: Record<string, string> = {
  all: "bg-blue-100 text-blue-800",
  admin: "bg-purple-100 text-purple-800",
  teacher: "bg-green-100 text-green-800",
  student: "bg-yellow-100 text-yellow-800",
  parent: "bg-orange-100 text-orange-800",
};

const audienceLabels: Record<string, string> = {
  all: "Everyone",
  admin: "Admins",
  teacher: "Teachers",
  student: "Students",
  parent: "Parents",
};

export default function AnnouncementsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  // State
  const [announcements, setAnnouncements] = useState<AnnouncementListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Filter state from URL params
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");
  const targetAudience = searchParams.get("target_audience") || "";

  // Local filter state
  const [audienceFilter, setAudienceFilter] = useState(targetAudience);

  // Check permissions
  const canCreateAnnouncement = user?.role === "admin" || user?.role === "super_admin" || user?.role === "teacher";
  const canDeleteAnnouncement = user?.role === "admin" || user?.role === "super_admin";

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
      router.push(`/dashboard/announcements?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Fetch announcements
  useEffect(() => {
    async function fetchAnnouncements() {
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {
          page,
          page_size: pageSize,
        };
        if (targetAudience) params.target_audience = targetAudience;

        const response = await api.get<AnnouncementListResponse>("/api/announcements", params);
        setAnnouncements(response.items);
        setTotalCount(response.total_count);
        setTotalPages(response.total_pages);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch announcements");
      } finally {
        setIsLoading(false);
      }
    }
    fetchAnnouncements();
  }, [page, pageSize, targetAudience]);

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({ target_audience: audienceFilter });
    setShowFilters(false);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setAudienceFilter("");
    router.push("/dashboard/announcements");
  };

  // Handle delete
  const handleDelete = async () => {
    if (!deleteId) return;

    setIsDeleting(true);
    try {
      await api.delete(`/api/announcements/${deleteId}`);
      toast.success("Announcement deleted successfully");
      setAnnouncements((prev) => prev.filter((a) => a.id !== deleteId));
      setTotalCount((prev) => prev - 1);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to delete announcement");
    } finally {
      setIsDeleting(false);
      setDeleteId(null);
    }
  };

  // Get author name
  const getAuthorName = (author: AuthorInfo | null) => {
    if (!author) return "Unknown";
    if (author.profile_data?.first_name || author.profile_data?.last_name) {
      return `${author.profile_data.first_name || ""} ${author.profile_data.last_name || ""}`.trim();
    }
    return author.email;
  };

  // Format date
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Truncate content
  const truncateContent = (content: string, maxLength: number = 100) => {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + "...";
  };

  // Check if user can edit announcement
  const canEditAnnouncement = (announcement: AnnouncementListItem) => {
    if (user?.role === "admin" || user?.role === "super_admin") return true;
    if (user?.role === "teacher" && announcement.created_by === user.id) return true;
    return false;
  };

  const hasActiveFilters = !!targetAudience;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Announcements</h1>
          <p className="text-muted-foreground">
            View and manage school announcements
          </p>
        </div>
        {canCreateAnnouncement && (
          <Link href="/dashboard/announcements/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Announcement
            </Button>
          </Link>
        )}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-2">
              <Megaphone className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {totalCount} announcement{totalCount !== 1 ? "s" : ""}
              </span>
            </div>

            <div className="flex gap-2">
              {(user?.role === "admin" || user?.role === "super_admin") && (
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
              )}
              {hasActiveFilters && (
                <Button variant="ghost" onClick={handleClearFilters}>
                  <X className="h-4 w-4 mr-2" />
                  Clear
                </Button>
              )}
            </div>
          </div>

          {/* Filter Panel - Admin only */}
          {showFilters && (user?.role === "admin" || user?.role === "super_admin") && (
            <div className="mt-4 pt-4 border-t">
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="text-sm font-medium mb-2 block">Target Audience</label>
                  <select
                    value={audienceFilter}
                    onChange={(e) => setAudienceFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Audiences</option>
                    <option value="all">Everyone</option>
                    <option value="admin">Admins</option>
                    <option value="teacher">Teachers</option>
                    <option value="student">Students</option>
                    <option value="parent">Parents</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <Button onClick={handleApplyFilters}>Apply Filters</Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Announcements Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Announcements</CardTitle>
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
          ) : announcements.length === 0 ? (
            <div className="text-center py-12">
              <Megaphone className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No announcements found</p>
              {hasActiveFilters && (
                <Button variant="link" onClick={handleClearFilters} className="mt-2">
                  Clear filters
                </Button>
              )}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Content</TableHead>
                    <TableHead>Audience</TableHead>
                    <TableHead>Author</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {announcements.map((announcement) => (
                    <TableRow key={announcement.id}>
                      <TableCell>
                        <p className="font-medium">{announcement.title}</p>
                      </TableCell>
                      <TableCell>
                        <p className="text-sm text-muted-foreground">
                          {truncateContent(announcement.content)}
                        </p>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={`${audienceColors[announcement.target_audience] || ""} gap-1`}
                        >
                          <Users className="h-3 w-3" />
                          {audienceLabels[announcement.target_audience] || announcement.target_audience}
                        </Badge>
                      </TableCell>
                      <TableCell>{getAuthorName(announcement.author)}</TableCell>
                      <TableCell>{formatDate(announcement.created_at)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Link href={`/dashboard/announcements/${announcement.id}`}>
                            <Button variant="ghost" size="icon-sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                          {canEditAnnouncement(announcement) && (
                            <Link href={`/dashboard/announcements/${announcement.id}/edit`}>
                              <Button variant="ghost" size="icon-sm">
                                <Edit className="h-4 w-4" />
                              </Button>
                            </Link>
                          )}
                          {canDeleteAnnouncement && (
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              className="text-red-600"
                              onClick={() => setDeleteId(announcement.id)}
                            >
                              <Trash2 className="h-4 w-4" />
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

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteId !== null}
        onOpenChange={(open) => !open && setDeleteId(null)}
        title="Delete Announcement"
        description="Are you sure you want to delete this announcement? This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={handleDelete}
        variant="destructive"
      />
    </div>
  );
}
