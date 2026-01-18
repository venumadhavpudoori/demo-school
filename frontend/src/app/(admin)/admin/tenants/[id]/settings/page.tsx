"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Save, Building2, CreditCard, Settings, Globe } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

// Types
interface TenantDetail {
  id: number;
  name: string;
  slug: string;
  domain: string | null;
  subscription_plan: string;
  status: string;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string | null;
  user_count: number;
  student_count: number;
  teacher_count: number;
  admin_count: number;
  active_user_count: number;
}

interface TenantUpdateData {
  name?: string;
  domain?: string;
  subscription_plan?: string;
  status?: string;
  settings?: Record<string, unknown>;
}

export default function TenantSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const tenantId = params.id as string;

  const [tenant, setTenant] = useState<TenantDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [subscriptionPlan, setSubscriptionPlan] = useState("");
  const [status, setStatus] = useState("");
  const [settingsJson, setSettingsJson] = useState("");
  const [settingsError, setSettingsError] = useState("");

  useEffect(() => {
    async function fetchTenant() {
      setIsLoading(true);
      try {
        const response = await api.get<TenantDetail>(`/api/admin/tenants/${tenantId}`);
        setTenant(response);
        setName(response.name);
        setDomain(response.domain || "");
        setSubscriptionPlan(response.subscription_plan);
        setStatus(response.status);
        setSettingsJson(JSON.stringify(response.settings, null, 2));
      } catch (err) {
        const apiError = err as ApiError;
        toast.error(apiError.message || "Failed to fetch tenant details");
        if (apiError.status === 404) {
          router.push("/admin/tenants");
        }
      } finally {
        setIsLoading(false);
      }
    }
    fetchTenant();
  }, [tenantId, router]);

  const validateSettings = (json: string): boolean => {
    if (!json.trim()) {
      setSettingsError("");
      return true;
    }
    try {
      JSON.parse(json);
      setSettingsError("");
      return true;
    } catch {
      setSettingsError("Invalid JSON format");
      return false;
    }
  };

  const handleSaveBasicInfo = async () => {
    if (!tenant) return;
    setIsSaving(true);
    try {
      const data: TenantUpdateData = {
        name: name.trim(),
        domain: domain.trim() || undefined,
      };
      const response = await api.put<TenantDetail>(`/api/admin/tenants/${tenantId}`, data);
      setTenant(response);
      toast.success("Basic information updated successfully");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to update tenant");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveSubscription = async () => {
    if (!tenant) return;
    setIsSaving(true);
    try {
      const data: TenantUpdateData = {
        subscription_plan: subscriptionPlan,
        status: status,
      };
      const response = await api.put<TenantDetail>(`/api/admin/tenants/${tenantId}`, data);
      setTenant(response);
      toast.success("Subscription updated successfully");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to update subscription");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!tenant) return;
    if (!validateSettings(settingsJson)) return;
    
    setIsSaving(true);
    try {
      const settings = settingsJson.trim() ? JSON.parse(settingsJson) : {};
      const response = await api.patch<TenantDetail>(
        `/api/admin/tenants/${tenantId}/settings`,
        { settings }
      );
      setTenant(response);
      setSettingsJson(JSON.stringify(response.settings, null, 2));
      toast.success("Settings updated successfully");
    } catch (err) {
      const apiError = err as ApiError;
      toast.error(apiError.message || "Failed to update settings");
    } finally {
      setIsSaving(false);
    }
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
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Tenant not found</p>
        <Button variant="link" onClick={() => router.push("/admin/tenants")} className="mt-2">
          Back to tenants
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">Configure {tenant.name}</h1>
          <p className="text-muted-foreground font-mono">{tenant.slug}</p>
        </div>
      </div>

      {/* Settings Tabs */}
      <Tabs defaultValue="basic" className="space-y-6">
        <TabsList>
          <TabsTrigger value="basic" className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Basic Info
          </TabsTrigger>
          <TabsTrigger value="subscription" className="flex items-center gap-2">
            <CreditCard className="h-4 w-4" />
            Subscription
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        {/* Basic Info Tab */}
        <TabsContent value="basic">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Basic Information
              </CardTitle>
              <CardDescription>
                Update the tenant&apos;s basic details
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="School name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="slug">Slug (read-only)</Label>
                  <Input
                    id="slug"
                    value={tenant.slug}
                    disabled
                    className="bg-muted"
                  />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="domain" className="flex items-center gap-2">
                    <Globe className="h-4 w-4" />
                    Custom Domain
                  </Label>
                  <Input
                    id="domain"
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                    placeholder="school.example.com"
                  />
                  <p className="text-xs text-muted-foreground">
                    Optional custom domain for this tenant
                  </p>
                </div>
              </div>
              <div className="flex justify-end">
                <Button onClick={handleSaveBasicInfo} disabled={isSaving}>
                  <Save className="h-4 w-4 mr-2" />
                  {isSaving ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Subscription Tab */}
        <TabsContent value="subscription">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="h-5 w-5" />
                Subscription & Status
              </CardTitle>
              <CardDescription>
                Manage the tenant&apos;s subscription plan and account status
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="plan">Subscription Plan</Label>
                  <select
                    id="plan"
                    value={subscriptionPlan}
                    onChange={(e) => setSubscriptionPlan(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="free">Free</option>
                    <option value="basic">Basic</option>
                    <option value="standard">Standard</option>
                    <option value="premium">Premium</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="status">Account Status</Label>
                  <select
                    id="status"
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                    <option value="suspended">Suspended</option>
                    <option value="trial">Trial</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end">
                <Button onClick={handleSaveSubscription} disabled={isSaving}>
                  <Save className="h-4 w-4 mr-2" />
                  {isSaving ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Custom Settings
              </CardTitle>
              <CardDescription>
                Configure custom settings for this tenant (JSON format)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="settings">Settings (JSON)</Label>
                <textarea
                  id="settings"
                  value={settingsJson}
                  onChange={(e) => {
                    setSettingsJson(e.target.value);
                    validateSettings(e.target.value);
                  }}
                  className="w-full h-64 rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
                  placeholder='{"key": "value"}'
                />
                {settingsError && (
                  <p className="text-sm text-destructive">{settingsError}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Enter custom configuration as valid JSON. These settings can be used to customize tenant behavior.
                </p>
              </div>
              <div className="flex justify-end">
                <Button 
                  onClick={handleSaveSettings} 
                  disabled={isSaving || !!settingsError}
                >
                  <Save className="h-4 w-4 mr-2" />
                  {isSaving ? "Saving..." : "Save Settings"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
