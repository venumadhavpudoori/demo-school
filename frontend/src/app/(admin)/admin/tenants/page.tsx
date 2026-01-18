"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  Settings,
  Filter,
  X,
  Building2,
  Users,
  GraduationCap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
interface TenantListItem {
  id: number;
  name: string;
  slug: string;
  domain: string | null;
  subscription_plan: string;
  status: string;
  created_at: string;
  updated_at: string | null;
  user_count: number;
  student_count: number;
  teacher_count: number;
}

interface TenantListResponse {
  items: TenantListItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-gray-100 text-gray-800",
  suspended: "bg-red-100 text-red-800",
  trial: "bg-blue-100 text-blue-800",
};

const planColors: Record<string, string> = {
  free: "bg-gray-100 text-gray-800",
  basic: "bg-blue-100 text-blue-800",
  standard: "bg-purple-100 text-purple-800",
  premium: "bg-amber-100 text-amber-800",
  enterprise: "bg-emerald-100 text-emerald-800",
};

export default function TenantsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // State
  const [tenants, setTenants] = useState<TenantListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state from URL params
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");
  const search = searchParams.get("search") || "";
  const statusFilter = searchParams.get("status") || "";
  const planFilter = searchParams.get("subscription_plan") || "";

  // Local filter state for inputs
  const [searchInput, setSearchInput] = useState(search);
  const [localStatusFilter, setLocalStatusFilter] = useState(statusFilter);
  const [localPlanFilter, setLocalPlanFilter] = useState(planFilter);

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
      router.push(`/admin/tenants?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Fetch tenants
  useEffect(() => {
    async function fetchTenants() {
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {
          page,
          page_size: pageSize,
        };
        if (search) params.search = search;
        if (statusFilter) params.status = statusFilter;
        if (planFilter) params.subscription_plan = planFilter;

        const response = await api.get<TenantListResponse>("/api/admin/tenants", params);
        setTenants(response.items);
        setTotalCount(response.total_count);
        setTotalPages(response.total_pages);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch tenants");
      } finally {
        setIsLoading(false);
      }
    }
    fetchTenants();
  }, [page, pageSize, search, statusFilter, planFilter]);

  // Handle search submit
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilters({ search: searchInput });
  };

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({
      status: localStatusFilter,
      subscription_plan: localPlanFilter,
    });
    setShowFilters(false);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setSearchInput("");
    setLocalStatusFilter("");
    setLocalPlanFilter("");
    router.push("/admin/tenants");
  };

  // Check if any filters are active
  const hasActiveFilters = search || statusFilter || planFilter;

  // Format date
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tenants</h1>
          <p className="text-muted-foreground">
            Manage schools and organizations on the platform
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tenants</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {tenants.reduce((sum, t) => sum + t.user_count, 0)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Students</CardTitle>
            <GraduationCap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {tenants.reduce((sum, t) => sum + t.student_count, 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            {/* Search */}
            <form onSubmit={handleSearch} className="flex gap-2 flex-1 max-w-md">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name, slug, or domain..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>

            {/* Filter Toggle */}
            <div className="flex gap-2">
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
              {hasActiveFilters && (
                <Button variant="ghost" onClick={handleClearFilters}>
                  <X className="h-4 w-4 mr-2" />
                  Clear
                </Button>
              )}
            </div>
          </div>

          {/* Filter Panel */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t">
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="text-sm font-medium mb-2 block">Status</label>
                  <select
                    value={localStatusFilter}
                    onChange={(e) => setLocalStatusFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Statuses</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                    <option value="suspended">Suspended</option>
                    <option value="trial">Trial</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Subscription Plan</label>
                  <select
                    value={localPlanFilter}
                    onChange={(e) => setLocalPlanFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Plans</option>
                    <option value="free">Free</option>
                    <option value="basic">Basic</option>
                    <option value="standard">Standard</option>
                    <option value="premium">Premium</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <Button onClick={handleApplyFilters} className="w-full">
                    Apply Filters
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tenants Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Tenant List</span>
            <span className="text-sm font-normal text-muted-foreground">
              {totalCount} tenant{totalCount !== 1 ? "s" : ""} found
            </span>
          </CardTitle>
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
          ) : tenants.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No tenants found</p>
              {hasActiveFilters && (
                <Button
                  variant="link"
                  onClick={handleClearFilters}
                  className="mt-2"
                >
                  Clear filters
                </Button>
              )}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Slug</TableHead>
                    <TableHead>Plan</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Users</TableHead>
                    <TableHead>Students</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tenants.map((tenant) => (
                    <TableRow key={tenant.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{tenant.name}</p>
                          {tenant.domain && (
                            <p className="text-sm text-muted-foreground">
                              {tenant.domain}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{tenant.slug}</TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={planColors[tenant.subscription_plan] || ""}
                        >
                          {tenant.subscription_plan}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={statusColors[tenant.status] || ""}
                        >
                          {tenant.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{tenant.user_count}</TableCell>
                      <TableCell>{tenant.student_count}</TableCell>
                      <TableCell>{formatDate(tenant.created_at)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Link href={`/admin/tenants/${tenant.id}`}>
                            <Button variant="ghost" size="icon">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                          <Link href={`/admin/tenants/${tenant.id}/settings`}>
                            <Button variant="ghost" size="icon">
                              <Settings className="h-4 w-4" />
                            </Button>
                          </Link>
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
    </div>
  );
}
