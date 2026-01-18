"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { useAuth } from "@/context/AuthContext";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Form validation schema
const announcementFormSchema = z.object({
  title: z.string().min(1, "Title is required").max(255, "Title must be 255 characters or less"),
  content: z.string().min(1, "Content is required"),
  target_audience: z.enum(["all", "admin", "teacher", "student", "parent"]),
});

type AnnouncementFormValues = z.infer<typeof announcementFormSchema>;

const TARGET_AUDIENCES = [
  { value: "all", label: "Everyone", description: "Visible to all users" },
  { value: "admin", label: "Admins Only", description: "Only visible to administrators" },
  { value: "teacher", label: "Teachers Only", description: "Only visible to teachers" },
  { value: "student", label: "Students Only", description: "Only visible to students" },
  { value: "parent", label: "Parents Only", description: "Only visible to parents" },
];

export default function NewAnnouncementPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Check permission
  const canCreateAnnouncement = user?.role === "admin" || user?.role === "super_admin" || user?.role === "teacher";

  const form = useForm<AnnouncementFormValues>({
    resolver: zodResolver(announcementFormSchema),
    defaultValues: {
      title: "",
      content: "",
      target_audience: "all",
    },
  });

  // Handle form submission
  const onSubmit = async (data: AnnouncementFormValues) => {
    if (!canCreateAnnouncement) {
      toast.error("You don't have permission to create announcements");
      return;
    }

    setIsSubmitting(true);
    try {
      await api.post("/api/announcements", data);
      toast.success("Announcement created successfully");
      router.push("/dashboard/announcements");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to create announcement");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!canCreateAnnouncement) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-muted-foreground">
              You don&apos;t have permission to create announcements.
            </p>
            <Link href="/dashboard/announcements">
              <Button variant="link">Go back to announcements</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard/announcements">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Create Announcement</h1>
          <p className="text-muted-foreground">
            Create a new announcement for your school
          </p>
        </div>
      </div>

      {/* Form */}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Announcement Details */}
          <Card>
            <CardHeader>
              <CardTitle>Announcement Details</CardTitle>
              <CardDescription>
                Enter the announcement information
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="title"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Title *</FormLabel>
                    <FormControl>
                      <Input placeholder="Enter announcement title" {...field} />
                    </FormControl>
                    <FormDescription>
                      A clear and concise title for the announcement
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="content"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Content *</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Enter announcement content"
                        className="min-h-[200px]"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      The full content of the announcement
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="target_audience"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Target Audience *</FormLabel>
                    <FormControl>
                      <select
                        {...field}
                        className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                      >
                        {TARGET_AUDIENCES.map((audience) => (
                          <option key={audience.value} value={audience.value}>
                            {audience.label}
                          </option>
                        ))}
                      </select>
                    </FormControl>
                    <FormDescription>
                      {TARGET_AUDIENCES.find((a) => a.value === field.value)?.description}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <Link href="/dashboard/announcements">
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </Link>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create Announcement"}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
