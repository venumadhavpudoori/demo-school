"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Filter,
  X,
  CreditCard,
  Calendar,
  Building2,
  Receipt,
  Download,
  FileText,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
interface TenantBillingInfo {
  id: number;
  name: string;
  slug: string;
  subscription_plan: string;
  status: string;
  created_at: string;
  updated_at: string | null;
}

interface TenantListResponse {
  items: TenantBillingInfo[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

// Simulated billing record type (for future implementation)
interface BillingRecord {
  id: string;
  tenant_id: number;
  tenant_name: string;
  type: "subscription" | "upgrade" | "downgrade" | "renewal";
  plan: string;
  amount: number;
  status: "paid" | "pending" | "failed" | "refunded";
  date: string;
  invoice_number: string;
}

const planPrices: Record<string, number> = {
  free: 0,
  basic: 29,
  standard: 79,
  premium: 199,
  enterprise: 499,
};

const planColors: Record<string, string> = {
  free: "bg-gray-100 text-gray-800",
  basic: "bg-blue-100 text-blue-800",
  standard: "bg-purple-100 text-purple-800",
  premium: "bg-amber-100 text-amber-800",
  enterprise: "bg-emerald-100 text-emerald-800",
};

const statusColors: Record<string, string> = {
  paid: "bg-green-100 text-green-800",
  pending: "bg-yellow-100 text-yellow-800",
  failed: "bg-red-100 text-red-800",
  refunded: "bg-gray-100 text-gray-800",
};

const typeLabels: Record<string, string> = {
  subscription: "New Subscription",
  upgrade: "Plan Upgrade",
  downgrade: "Plan Downgrade",
  renewal: "Renewal",
};

export default function BillingHistoryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // State
  const [tenants, setTenants] = useState<TenantBillingInfo[]>([]);
  const [billingRecords, setBillingRecords] = useState<BillingRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [showFilters, setShowFilters] = useState(false);

  // Stats
  const [totalRevenue, setTotalRevenue] = useState(0);
  const [monthlyRevenue, setMonthlyRevenue] = useState(0);

  // Filter state from URL params
  const page = parseInt(searchParams.get("page") || "1");
  const pageSize = parseInt(searchParams.get("page_size") || "20");
  const planFilter = searchParams.get("plan") || "";
  const statusFilter = searchParams.get("status") || "";

  // Local filter state
  const [localPlanFilter, setLocalPlanFilter] = useState(planFilter);
  const [localStatusFilter, setLocalStatusFilter] = useState(statusFilter);

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
      router.push(`/admin/subscriptions/billing?${params.toString()}`);
    },
    [router, searchParams]
  );

  // Generate simulated billing records from tenant data
  const generateBillingRecords = (tenants: TenantBillingInfo[]): BillingRecord[] => {
    const records: BillingRecord[] = [];
    
    tenants.forEach((tenant) => {
      // Initial subscription record
      records.push({
        id: `${tenant.id}-initial`,
        tenant_id: tenant.id,
        tenant_name: tenant.name,
        type: "subscription",
        plan: tenant.subscription_plan,
        amount: planPrices[tenant.subscription_plan] || 0,
        status: tenant.status === "active" ? "paid" : "pending",
        date: tenant.created_at,
        invoice_number: `INV-${tenant.id.toString().padStart(6, "0")}`,
      });

      // If updated, add a plan change record
      if (tenant.updated_at && tenant.updated_at !== tenant.created_at) {
        records.push({
          id: `${tenant.id}-update`,
          tenant_id: tenant.id,
          tenant_name: tenant.name,
          type: "renewal",
          plan: tenant.subscription_plan,
          amount: planPrices[tenant.subscription_plan] || 0,
          status: "paid",
          date: tenant.updated_at,
          invoice_number: `INV-${tenant.id.toString().padStart(6, "0")}-R`,
        });
      }
    });

    // Sort by date descending
    return records.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  };

  // Fetch tenants and generate billing records
  useEffect(() => {
    async function fetchData() {
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = {
          page: 1,
          page_size: 1000, // Get all for billing calculation
        };

        const response = await api.get<TenantListResponse>("/api/admin/tenants", params);
        setTenants(response.items);

        // Generate billing records
        const records = generateBillingRecords(response.items);
        
        // Apply filters
        let filteredRecords = records;
        if (planFilter) {
          filteredRecords = filteredRecords.filter((r) => r.plan === planFilter);
        }
        if (statusFilter) {
          filteredRecords = filteredRecords.filter((r) => r.status === statusFilter);
        }

        // Calculate totals
        const total = records.reduce((sum, r) => sum + (r.status === "paid" ? r.amount : 0), 0);
        setTotalRevenue(total);

        // Calculate monthly revenue (current month)
        const now = new Date();
        const currentMonth = now.getMonth();
        const currentYear = now.getFullYear();
        const monthly = records
          .filter((r) => {
            const recordDate = new Date(r.date);
            return (
              recordDate.getMonth() === currentMonth &&
              recordDate.getFullYear() === currentYear &&
              r.status === "paid"
            );
          })
          .reduce((sum, r) => sum + r.amount, 0);
        setMonthlyRevenue(monthly);

        // Paginate
        setTotalCount(filteredRecords.length);
        setTotalPages(Math.ceil(filteredRecords.length / pageSize));
        
        const startIdx = (page - 1) * pageSize;
        const paginatedRecords = filteredRecords.slice(startIdx, startIdx + pageSize);
        setBillingRecords(paginatedRecords);
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch billing data");
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [page, pageSize, planFilter, statusFilter]);

  // Handle filter apply
  const handleApplyFilters = () => {
    updateFilters({
      plan: localPlanFilter,
      status: localStatusFilter,
    });
    setShowFilters(false);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setLocalPlanFilter("");
    setLocalStatusFilter("");
    router.push("/admin/subscriptions/billing");
  };

  // Check if any filters are active
  const hasActiveFilters = planFilter || statusFilter;

  // Format date
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Billing History</h1>
            <p className="text-muted-foreground">
              View subscription billing and payment history
            </p>
          </div>
        </div>
        <Link href="/admin/subscriptions">
          <Button variant="outline">
            <CreditCard className="h-4 w-4 mr-2" />
            Manage Plans
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <Receipt className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(totalRevenue)}</div>
            <p className="text-xs text-muted-foreground">All time</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Revenue</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(monthlyRevenue)}</div>
            <p className="text-xs text-muted-foreground">Current month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Subscriptions</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {tenants.filter((t) => t.status === "active").length}
            </div>
            <p className="text-xs text-muted-foreground">Paying tenants</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Transactions</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalCount}</div>
            <p className="text-xs text-muted-foreground">Billing records</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
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
            <Button variant="outline" disabled>
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          </div>

          {/* Filter Panel */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t">
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="text-sm font-medium mb-2 block">Plan</label>
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
                <div>
                  <label className="text-sm font-medium mb-2 block">Status</label>
                  <select
                    value={localStatusFilter}
                    onChange={(e) => setLocalStatusFilter(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="">All Statuses</option>
                    <option value="paid">Paid</option>
                    <option value="pending">Pending</option>
                    <option value="failed">Failed</option>
                    <option value="refunded">Refunded</option>
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

      {/* Billing Records Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Billing Records</span>
            <span className="text-sm font-normal text-muted-foreground">
              {totalCount} record{totalCount !== 1 ? "s" : ""} found
            </span>
          </CardTitle>
          <CardDescription>
            Subscription payments and billing transactions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                  <Skeleton className="h-8 w-20" />
                </div>
              ))}
            </div>
          ) : billingRecords.length === 0 ? (
            <div className="text-center py-12">
              <Receipt className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No billing records found</p>
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
                    <TableHead>Invoice</TableHead>
                    <TableHead>Tenant</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Plan</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {billingRecords.map((record) => (
                    <TableRow key={record.id}>
                      <TableCell className="font-mono text-sm">
                        {record.invoice_number}
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium">{record.tenant_name}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm">{typeLabels[record.type]}</span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={planColors[record.plan] || ""}
                        >
                          {record.plan}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">
                        {formatCurrency(record.amount)}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={statusColors[record.status] || ""}
                        >
                          {record.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatDate(record.date)}</TableCell>
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

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">About Billing History</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            This page displays billing records generated from tenant subscription data. 
            In a production environment, this would be connected to a payment processor 
            (like Stripe) to show actual payment transactions, invoices, and receipts.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
