"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Filter,
  X,
  CreditCard,
  Building2,
  TrendingUp,
  Edit,
  Check,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
interface TenantSubscription {
  id: number;
  name: string;
  slug: string;
  subscription_plan: string;
  status: string;
  created_at: string;
  user_count: number;
  student_count: number;
}

interface TenantListResponse {
  items: TenantSubscription[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

interface SubscriptionPlanInfo {
  name: string;
  value: string;
  description: string;
  features: string[];
  color: string;
  recommended?: boolean;
}

// Subscription plan definitions
const SUBSCRIPTION_PLANS: SubscriptionPlanInfo[] = [
  {
    name: "Free",
    value: "free",
    description: "Basic features for small schools",
    features: ["Up to 50 students", "Basic attendance", "Limited reports"],
    color: "bg-gray-100 text-gray-800",
  },
  {
    name: "Basic",
    value: "basic",
    description: "Essential features for growing schools",
    features: ["Up to 200 students", "Full attendance", "Basic analytics", "Email support"],
    color: "bg-blue-100 text-blue-800",
  },
  {
    name: "Standard",
    value: "standard",
    description: "Complete solution for medium schools",
    features: ["Up to 500 students", "All features", "Advanced analytics", "Priority support"],
    color: "bg-purple-100 text-purple-800",
    recommended: true,
  },
  {
    name: "Premium",
    value: "premium",
    description: "Advanced features for large schools",
    features: ["Up to 2000 students", "Custom reports", "API access", "Dedicated support"],
    color: "bg-amber-100 text-amber-800",
  },
  {
    name: "Enterprise",
    value: "enterprise",
    description: "Unlimited features for institutions",
    features: ["Unlimited students", "White-label option", "Custom integrations", "24/7 support"],
    color: "bg-emerald-100 text-emerald-800",
  },
];

const planColors: Record<string, string> = {
  free: "bg-gray-100 text-gray-800",
  basic: "bg-blue-100 text-blue-800",
  standard: "bg-purple-100 text-purple-800",
  premium: "bg-amber-100 text-amber-800",
  enterprise: "bg-emerald-100 text-emerald-800",
};

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-gray-100 text-gray-800",
  suspended: "bg-red-100 text-red-800",
  trial: "bg-blue-100 text-blue-800",
};

export default function SubscriptionsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // State
  const [tenants, setTenants] = useState<TenantSubscription[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const [planCounts, setPlanCounts] = useState<Record<string, number>>({});

  // Edit plan dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<TenantSubscription | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<string>("");
  const [isUpdating, setIsUpdating] = useState(false);

  // Filter state from URL params
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");
  const search = searchParams.get("search") || "";
  const planFilter = searchParams.get("subscription_plan") || "";

  // Local filter state for inputs
  const [searchInput, setSearchInput] = useState(search);
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
      router.push(`/admin/subscriptions?${params.toString()}`);
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
        if (planFilter) params.subscription_plan = planFilter;

        const response = await api.get<TenantListResponse>("/api/admin/tenants", params);
        setTenants(response.items);
        setTotalCount(response.total_count);
        setTotalPages(response.total_pages);

        // Calculate plan counts from all tenants (fetch all for stats)
        const allTenantsResponse = await api.get<TenantListResponse>("/api/admin/tenants", {
          page: 1,
          page_size: 1000,
        });
        const counts: Record<string, number> = {};
        allTenantsResponse.items.forEach((t) => {
          counts[t.subscription_plan] = (counts[t.subscription_plan] || 0) + 1;
        });
        setPlanCounts(counts);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch subscriptions");
      } finally {
        setIsLoading(false);
      }
    }
    fetchTenants();
  }, [page, pageSize, search, planFilter]);

  // Handle search submit
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilters({ search: searchInput });
  };

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({
      subscription_plan: localPlanFilter,
    });
    setShowFilters(false);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setSearchInput("");
    setLocalPlanFilter("");
    router.push("/admin/subscriptions");
  };

  // Open edit plan dialog
  const handleEditPlan = (tenant: TenantSubscription) => {
    setSelectedTenant(tenant);
    setSelectedPlan(tenant.subscription_plan);
    setEditDialogOpen(true);
  };

  // Update tenant subscription plan
  const handleUpdatePlan = async () => {
    if (!selectedTenant || !selectedPlan) return;

    setIsUpdating(true);
    try {
      await api.put(`/api/admin/tenants/${selectedTenant.id}`, {
        subscription_plan: selectedPlan,
      });
      toast.success(`Subscription plan updated to ${selectedPlan}`);
      setEditDialogOpen(false);
      // Refresh the list
      const params: Record<string, string | number> = {
        page,
        page_size: pageSize,
      };
      if (search) params.search = search;
      if (planFilter) params.subscription_plan = planFilter;
      const response = await api.get<TenantListResponse>("/api/admin/tenants", params);
      setTenants(response.items);
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to update subscription plan");
    } finally {
      setIsUpdating(false);
    }
  };

  // Check if any filters are active
  const hasActiveFilters = search || planFilter;

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
          <h1 className="text-2xl font-bold">Subscription Plans</h1>
          <p className="text-muted-foreground">
            Manage tenant subscription plans and billing
          </p>
        </div>
        <Link href="/admin/subscriptions/billing">
          <Button variant="outline">
            <CreditCard className="h-4 w-4 mr-2" />
            Billing History
          </Button>
        </Link>
      </div>

      {/* Plan Overview Cards */}
      <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-5">
        {SUBSCRIPTION_PLANS.map((plan) => (
          <Card
            key={plan.value}
            className={`cursor-pointer transition-all hover:shadow-md ${
              planFilter === plan.value ? "ring-2 ring-primary" : ""
            }`}
            onClick={() => {
              if (planFilter === plan.value) {
                updateFilters({ subscription_plan: "" });
              } else {
                updateFilters({ subscription_plan: plan.value });
              }
            }}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span>{plan.name}</span>
                {plan.recommended && (
                  <Badge variant="secondary" className="text-xs">
                    Popular
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{planCounts[plan.value] || 0}</div>
              <p className="text-xs text-muted-foreground">tenants</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Stats Summary */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Subscriptions</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalCount}</div>
            <p className="text-xs text-muted-foreground">
              Active tenant subscriptions
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Paid Plans</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(planCounts["basic"] || 0) +
                (planCounts["standard"] || 0) +
                (planCounts["premium"] || 0) +
                (planCounts["enterprise"] || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Tenants on paid plans
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Free Tier</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{planCounts["free"] || 0}</div>
            <p className="text-xs text-muted-foreground">
              Tenants on free plan
            </p>
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
                  placeholder="Search by tenant name..."
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
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium mb-2 block">Subscription Plan</label>
                  <select
                    value={localPlanFilter}
                    onChange={(e) => setLocalPlanFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Plans</option>
                    {SUBSCRIPTION_PLANS.map((plan) => (
                      <option key={plan.value} value={plan.value}>
                        {plan.name}
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
            </div>
          )}
        </CardContent>
      </Card>

      {/* Subscriptions Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Tenant Subscriptions</span>
            <span className="text-sm font-normal text-muted-foreground">
              {totalCount} subscription{totalCount !== 1 ? "s" : ""} found
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
              <p className="text-muted-foreground">No subscriptions found</p>
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
                    <TableHead>Tenant</TableHead>
                    <TableHead>Current Plan</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Users</TableHead>
                    <TableHead>Students</TableHead>
                    <TableHead>Since</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tenants.map((tenant) => (
                    <TableRow key={tenant.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{tenant.name}</p>
                          <p className="text-sm text-muted-foreground font-mono">
                            {tenant.slug}
                          </p>
                        </div>
                      </TableCell>
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
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditPlan(tenant)}
                        >
                          <Edit className="h-4 w-4 mr-1" />
                          Change Plan
                        </Button>
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

      {/* Edit Plan Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Change Subscription Plan</DialogTitle>
            <DialogDescription>
              Update the subscription plan for {selectedTenant?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Current Plan</Label>
              <Badge
                variant="secondary"
                className={planColors[selectedTenant?.subscription_plan || ""] || ""}
              >
                {selectedTenant?.subscription_plan}
              </Badge>
            </div>
            <div className="space-y-2">
              <Label>Select New Plan</Label>
              <div className="grid gap-2">
                {SUBSCRIPTION_PLANS.map((plan) => (
                  <div
                    key={plan.value}
                    className={`p-3 border rounded-lg cursor-pointer transition-all ${
                      selectedPlan === plan.value
                        ? "border-primary bg-primary/5"
                        : "hover:border-muted-foreground/50"
                    }`}
                    onClick={() => setSelectedPlan(plan.value)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className={plan.color}>
                          {plan.name}
                        </Badge>
                        {plan.recommended && (
                          <Badge variant="outline" className="text-xs">
                            Recommended
                          </Badge>
                        )}
                      </div>
                      {selectedPlan === plan.value && (
                        <Check className="h-4 w-4 text-primary" />
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {plan.description}
                    </p>
                    <ul className="text-xs text-muted-foreground mt-2 space-y-1">
                      {plan.features.map((feature, idx) => (
                        <li key={idx}>• {feature}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleUpdatePlan}
              disabled={isUpdating || selectedPlan === selectedTenant?.subscription_plan}
            >
              {isUpdating ? "Updating..." : "Update Plan"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
