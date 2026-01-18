"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Edit, Trash2, Users, Calendar, User } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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

interface AnnouncementResponse {
  id: number;
  title: string;
  content: string;
  target_audience: string;
  created_by: number | null;
  author: AuthorInfo | null;
  created_at: string | null;
  updated_at: string | null;
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

export default function AnnouncementDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const announcementId = params.id as string;

  const [announcement, setAnnouncement] = useState<AnnouncementResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Check permissions
  const canDeleteAnnouncement = user?.role === "admin" || user?.role === "super_admin";
  const canEditAnnouncement = () => {
    if (!announcement) return false;
    if (user?.role === "admin" || user?.role === "super_admin") return true;
    if (user?.role === "teacher" && announcement.created_by === user.id) return true;
    return false;
  };

  // Fetch announcement
  useEffect(() => {
    async function fetchAnnouncement() {
      setIsLoading(true);
      try {
        const response = await api.get<AnnouncementResponse>(`/api/announcements/${announcementId}`);
        setAnnouncement(response);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch announcement");
        router.push("/dashboard/announcements");
      } finally {
        setIsLoading(false);
      }
    }
    fetchAnnouncement();
  }, [announcementId, router]);

  // Handle delete
  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.delete(`/api/announcements/${announcementId}`);
      toast.success("Announcement deleted successfully");
      router.push("/dashboard/announcements");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to delete announcement");
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
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
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
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
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!announcement) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/announcements">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{announcement.title}</h1>
            <p className="text-muted-foreground">Announcement Details</p>
          </div>
        </div>
        <div className="flex gap-2">
          {canEditAnnouncement() && (
            <Link href={`/dashboard/announcements/${announcementId}/edit`}>
              <Button variant="outline">
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
            </Link>
          )}
          {canDeleteAnnouncement && (
            <Button
              variant="outline"
              className="text-red-600 hover:text-red-700"
              onClick={() => setShowDeleteDialog(true)}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          )}
        </div>
      </div>

      {/* Announcement Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{announcement.title}</CardTitle>
            <Badge
              variant="secondary"
              className={`${audienceColors[announcement.target_audience] || ""} gap-1`}
            >
              <Users className="h-3 w-3" />
              {audienceLabels[announcement.target_audience] || announcement.target_audience}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Content */}
          <div className="prose max-w-none">
            <p className="whitespace-pre-wrap">{announcement.content}</p>
          </div>

          {/* Metadata */}
          <div className="border-t pt-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <User className="h-4 w-4" />
                <span>Posted by: {getAuthorName(announcement.author)}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span>Created: {formatDate(announcement.created_at)}</span>
              </div>
              {announcement.updated_at && announcement.updated_at !== announcement.created_at && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  <span>Updated: {formatDate(announcement.updated_at)}</span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Announcement"
        description="Are you sure you want to delete this announcement? This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={handleDelete}
        variant="destructive"
      />
    </div>
  );
}
