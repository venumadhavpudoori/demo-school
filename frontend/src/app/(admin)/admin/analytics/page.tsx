"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Building2, 
  Users, 
  GraduationCap, 
  DollarSign, 
  TrendingUp, 
  TrendingDown,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface PlatformOverview {
  total_tenants: number;
  active_tenants: number;
  total_users: number;
  total_students: number;
  total_teachers: number;
  total_revenue: number;
  pending_revenue: number;
}

interface SubscriptionBreakdown {
  plan: string;
  count: number;
  percentage: number;
}

interface GrowthMetric {
  period: string;
  value: number;
  previous_value: number;
  growth_percentage: number;
}

interface ChartData {
  month: string;
  count?: number;
  amount?: number;
}

interface PlatformAnalytics {
  overview: PlatformOverview;
  subscription_breakdown: SubscriptionBreakdown[];
  tenant_growth: GrowthMetric;
  user_growth: GrowthMetric;
  revenue_growth: GrowthMetric;
  tenant_growth_chart: ChartData[];
  user_growth_chart: ChartData[];
  revenue_chart: ChartData[];
}

interface TenantStatusBreakdown {
  status: string;
  count: number;
  percentage: number;
}

interface TopTenant {
  id: number;
  name: string;
  slug: string;
  user_count: number;
  student_count: number;
  subscription_plan: string;
}

interface DetailedAnalytics {
  tenant_status_breakdown: TenantStatusBreakdown[];
  top_tenants_by_users: TopTenant[];
  average_users_per_tenant: number;
  average_students_per_tenant: number;
  average_teachers_per_tenant: number;
}

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884D8", "#82CA9D"];
const STATUS_COLORS: Record<string, string> = {
  active: "#22c55e",
  suspended: "#ef4444",
  trial: "#eab308",
  inactive: "#6b7280",
};

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatNumber(num: number): string {
  return new Intl.NumberFormat("en-US").format(num);
}

function GrowthIndicator({ percentage }: { percentage: number }) {
  if (percentage === 0) {
    return <span className="text-muted-foreground text-sm">No change</span>;
  }
  
  const isPositive = percentage > 0;
  return (
    <span className={`flex items-center text-sm ${isPositive ? "text-green-600" : "text-red-600"}`}>
      {isPositive ? <TrendingUp className="h-4 w-4 mr-1" /> : <TrendingDown className="h-4 w-4 mr-1" />}
      {Math.abs(percentage).toFixed(1)}%
    </span>
  );
}

export default function AnalyticsDashboardPage() {
  const [analytics, setAnalytics] = useState<PlatformAnalytics | null>(null);
  const [detailedAnalytics, setDetailedAnalytics] = useState<DetailedAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchAnalytics() {
      try {
        setLoading(true);
        setError(null);
        
        const [platformData, detailedData] = await Promise.all([
          api.get<PlatformAnalytics>("/api/admin/analytics"),
          api.get<DetailedAnalytics>("/api/admin/analytics/detailed"),
        ]);
        
        setAnalytics(platformData);
        setDetailedAnalytics(detailedData);
      } catch (err) {
        console.error("Failed to fetch analytics:", err);
        setError("Failed to load analytics data. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!analytics || !detailedAnalytics) {
    return null;
  }

  const { overview, subscription_breakdown, tenant_growth, user_growth, revenue_growth } = analytics;

  // Prepare pie chart data for subscriptions
  const subscriptionPieData = subscription_breakdown.map((item) => ({
    name: item.plan.charAt(0).toUpperCase() + item.plan.slice(1),
    value: item.count,
  }));

  // Prepare pie chart data for tenant status
  const statusPieData = detailedAnalytics.tenant_status_breakdown.map((item) => ({
    name: item.status.charAt(0).toUpperCase() + item.status.slice(1),
    value: item.count,
    color: STATUS_COLORS[item.status] || "#6b7280",
  }));

  // Prepare combined growth chart data
  const combinedGrowthData = analytics.tenant_growth_chart.map((item, index) => ({
    month: item.month,
    tenants: item.count || 0,
    users: analytics.user_growth_chart[index]?.count || 0,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Platform Analytics</h1>
        <p className="text-muted-foreground">
          Comprehensive overview of platform performance and growth metrics
        </p>
      </div>

      {/* Overview Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tenants</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(overview.total_tenants)}</div>
            <p className="text-xs text-muted-foreground">
              {overview.active_tenants} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(overview.total_users)}</div>
            <p className="text-xs text-muted-foreground">
              Across all tenants
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Students</CardTitle>
            <GraduationCap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(overview.total_students)}</div>
            <p className="text-xs text-muted-foreground">
              {overview.total_teachers} teachers
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(overview.total_revenue)}</div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(overview.pending_revenue)} pending
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Growth Metrics */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Tenant Growth</CardTitle>
            <CardDescription>{tenant_growth.period}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-bold">+{tenant_growth.value}</span>
              <GrowthIndicator percentage={tenant_growth.growth_percentage} />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              vs {tenant_growth.previous_value} last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">User Growth</CardTitle>
            <CardDescription>{user_growth.period}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-bold">+{user_growth.value}</span>
              <GrowthIndicator percentage={user_growth.growth_percentage} />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              vs {user_growth.previous_value} last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Revenue Growth</CardTitle>
            <CardDescription>{revenue_growth.period}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-bold">{formatCurrency(revenue_growth.value)}</span>
              <GrowthIndicator percentage={revenue_growth.growth_percentage} />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              vs {formatCurrency(revenue_growth.previous_value)} last month
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for Charts and Details */}
      <Tabs defaultValue="charts" className="space-y-4">
        <TabsList>
          <TabsTrigger value="charts">Growth Charts</TabsTrigger>
          <TabsTrigger value="breakdown">Breakdown</TabsTrigger>
          <TabsTrigger value="top-tenants">Top Tenants</TabsTrigger>
        </TabsList>

        <TabsContent value="charts" className="space-y-4">
          {/* Combined Growth Area Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Platform Growth Overview</CardTitle>
              <CardDescription>Tenant and user growth over time</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={combinedGrowthData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis 
                      dataKey="month" 
                      tick={{ fontSize: 12 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis 
                      tick={{ fontSize: 12 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                      }}
                    />
                    <Legend />
                    <Area 
                      type="monotone" 
                      dataKey="tenants" 
                      stackId="1"
                      stroke="#0088FE" 
                      fill="#0088FE" 
                      fillOpacity={0.6}
                      name="Tenants"
                    />
                    <Area 
                      type="monotone" 
                      dataKey="users" 
                      stackId="2"
                      stroke="#00C49F" 
                      fill="#00C49F" 
                      fillOpacity={0.6}
                      name="Users"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            {/* Revenue Bar Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Monthly Revenue</CardTitle>
                <CardDescription>Revenue collected per month</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analytics.revenue_chart}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis 
                        dataKey="month" 
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis 
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(value) => `$${value}`}
                      />
                      <Tooltip 
                        formatter={(value) => [formatCurrency(value as number), "Revenue"]}
                        contentStyle={{ 
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Bar 
                        dataKey="amount" 
                        fill="#8884D8" 
                        radius={[4, 4, 0, 0]}
                        name="Revenue"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* User Growth Line Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">User Growth Trend</CardTitle>
                <CardDescription>Cumulative users over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={analytics.user_growth_chart}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis 
                        dataKey="month" 
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis 
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="count" 
                        stroke="#00C49F" 
                        strokeWidth={2}
                        dot={{ fill: "#00C49F", strokeWidth: 2 }}
                        name="Users"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="breakdown" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Subscription Pie Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Subscription Plans</CardTitle>
                <CardDescription>Distribution by plan type</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={subscriptionPieData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {subscriptionPieData.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Tenant Status Pie Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Tenant Status</CardTitle>
                <CardDescription>Distribution by status</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={statusPieData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {statusPieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Average Metrics */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Average Metrics</CardTitle>
              <CardDescription>Per-tenant averages</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="text-center p-4 bg-muted rounded-lg">
                  <div className="text-2xl font-bold">{detailedAnalytics.average_users_per_tenant}</div>
                  <p className="text-sm text-muted-foreground">Avg Users/Tenant</p>
                </div>
                <div className="text-center p-4 bg-muted rounded-lg">
                  <div className="text-2xl font-bold">{detailedAnalytics.average_students_per_tenant}</div>
                  <p className="text-sm text-muted-foreground">Avg Students/Tenant</p>
                </div>
                <div className="text-center p-4 bg-muted rounded-lg">
                  <div className="text-2xl font-bold">{detailedAnalytics.average_teachers_per_tenant}</div>
                  <p className="text-sm text-muted-foreground">Avg Teachers/Tenant</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Top Tenants Bar Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Top Tenants Comparison</CardTitle>
              <CardDescription>Users and students by tenant</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart 
                    data={detailedAnalytics.top_tenants_by_users.slice(0, 5)}
                    layout="vertical"
                  >
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis type="number" tick={{ fontSize: 11 }} />
                    <YAxis 
                      dataKey="name" 
                      type="category" 
                      tick={{ fontSize: 11 }}
                      width={100}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                      }}
                    />
                    <Legend />
                    <Bar dataKey="user_count" fill="#0088FE" name="Users" />
                    <Bar dataKey="student_count" fill="#00C49F" name="Students" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="top-tenants">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Top Tenants by Users</CardTitle>
              <CardDescription>Schools with the most users</CardDescription>
            </CardHeader>
            <CardContent>
              {detailedAnalytics.top_tenants_by_users.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No tenants found
                </p>
              ) : (
                <div className="space-y-4">
                  {detailedAnalytics.top_tenants_by_users.map((tenant, index) => (
                    <div 
                      key={tenant.id} 
                      className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-lg font-bold text-muted-foreground w-6">
                          #{index + 1}
                        </span>
                        <div>
                          <p className="font-medium">{tenant.name}</p>
                          <p className="text-sm text-muted-foreground">{tenant.slug}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-6 text-sm">
                        <div className="text-center">
                          <p className="font-medium">{tenant.user_count}</p>
                          <p className="text-muted-foreground">Users</p>
                        </div>
                        <div className="text-center">
                          <p className="font-medium">{tenant.student_count}</p>
                          <p className="text-muted-foreground">Students</p>
                        </div>
                        <div className="text-center">
                          <span className="px-2 py-1 bg-primary/10 text-primary rounded text-xs capitalize">
                            {tenant.subscription_plan}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
