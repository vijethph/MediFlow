"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Pill, Plus, User, Search, Download } from "lucide-react";
import { usePrescriptions, useRequestRefill } from "@/lib/hooks/usePrescriptions";
import { authApi } from "@/lib/api/auth";
import { useNotificationContext } from "@/components/providers/NotificationProvider";

export default function PrescriptionsPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  const { success, error: showError } = useNotificationContext();
  
  useEffect(() => {
    if (!authApi.isAuthenticated()) {
      router.replace("/login");
      return;
    }
  }, [router]);
  
  if (!authApi.isAuthenticated()) {
    return null;
  }
  
  const { data, isLoading, error } = usePrescriptions();
  const requestRefill = useRequestRefill();

  const prescriptions = data?.items || [];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "active";
      case "pending":
        return "pending";
      case "expired":
        return "expired";
      case "filled":
        return "filled";
      default:
        return "active";
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const filteredPrescriptions = prescriptions.filter((p) => {
    // Status filtering
    if (statusFilter && p.status !== statusFilter) {
      return false;
    }
    
    // Search filtering
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesSearch = 
        (p.medication || "").toLowerCase().includes(query) ||
        (p.dosage || "").toLowerCase().includes(query) ||
        (p.doctor_name || p.doctor_id || "").toLowerCase().includes(query);
      if (!matchesSearch) return false;
    }
    
    return true;
  });

  // Calculate pagination on filtered results
  const totalPages = Math.ceil(filteredPrescriptions.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;

  // Apply pagination
  const paginatedPrescriptions = filteredPrescriptions.slice(startIndex, endIndex);

  const handleRefill = async (prescriptionId: string) => {
    if (confirm("Request refill for this prescription?")) {
      try {
        await requestRefill.mutateAsync(prescriptionId);
        success("Refill Requested", "Your prescription refill request has been submitted successfully.");
        router.refresh();
      } catch (err: any) {
        showError("Refill Failed", err.message || "Failed to request refill. Please try again.");
      }
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-8">
        <ErrorMessage message="Failed to load prescriptions. Please try again." />
      </div>
    );
  }

  const activeCount = prescriptions.filter((p) => p.status === "active").length;
  const pendingRefillCount = prescriptions.filter(
    (p) => p.status === "pending" || p.refills_remaining === 0
  ).length;
  const expiredCount = prescriptions.filter((p) => p.status === "expired").length;

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">My Prescriptions</h1>
          <p className="text-base text-gray-600">Manage prescriptions and medications</p>
        </div>
        <Link href="/prescriptions/create">
          <Button variant="primary" className="mt-4 sm:mt-0 bg-purple-600 hover:bg-purple-700">
            <Plus className="w-4 h-4" aria-hidden="true" />
            New Prescription
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Active</p>
              <p className="text-3xl font-bold text-gray-900">{activeCount}</p>
            </div>
            <div className="p-4 bg-blue-100 rounded-xl">
              <Pill className="w-8 h-8 text-blue-600" aria-hidden="true" />
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Pending Refill</p>
              <p className="text-3xl font-bold text-gray-900">{pendingRefillCount}</p>
            </div>
            <div className="p-4 bg-yellow-100 rounded-xl">
              <Pill className="w-8 h-8 text-yellow-600" aria-hidden="true" />
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Expired</p>
              <p className="text-3xl font-bold text-gray-900">{expiredCount}</p>
            </div>
            <div className="p-4 bg-red-100 rounded-xl">
              <Pill className="w-8 h-8 text-red-600" aria-hidden="true" />
            </div>
          </div>
        </Card>
      </div>

      {/* Search Bar */}
      <Card className="mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative min-w-0">
            <Search 
              className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" 
              aria-hidden="true" 
            />
            <input
              type="text"
              placeholder="Search prescriptions by patient, medication..."
              className="input pl-10 w-full"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search prescriptions"
            />
          </div>
          <select
            className="input md:w-40 w-full shrink-0"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="pending">Pending</option>
            <option value="expired">Expired</option>
            <option value="filled">Filled</option>
          </select>
        </div>
      </Card>

      {/* Prescriptions List */}
      {filteredPrescriptions.length > 0 ? (
        <div className="space-y-4">
          {filteredPrescriptions.map((prescription) => (
            <Card key={prescription.id} hoverable>
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {prescription.medication}
                    </h3>
                    <StatusBadge status={getStatusColor(prescription.status)}>
                      {prescription.status === "active" ? "Active" :
                       prescription.status === "pending" ? "Pending" :
                       prescription.status === "expired" ? "Expired" :
                       prescription.status === "filled" ? "Filled" :
                       prescription.status}
                    </StatusBadge>
                  </div>
                  <p className="text-sm text-gray-600 mb-1">{prescription.dosage}</p>
                  {(prescription.doctor_name || prescription.doctor_id) && (
                    <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
                      <User className="w-4 h-4" aria-hidden="true" />
                      <span>Prescribed by {prescription.doctor_name || prescription.doctor_id}</span>
                    </div>
                  )}
                  <div className="text-sm text-gray-600">
                    <p>Prescribed {formatDate(prescription.start_date || "")} to {formatDate(prescription.end_date || "")}</p>
                    <p className="mt-1">{prescription.refills_remaining} refills remaining</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Link href={`/prescriptions/${prescription.id}`}>
                    <Button variant="secondary">View Details</Button>
                  </Link>
                  {prescription.status === "active" && (prescription.refills_remaining === undefined || prescription.refills_remaining > 0) && (
                    <Button
                      variant="primary"
                      onClick={() => handleRefill(prescription.id)}
                      disabled={requestRefill.isPending}
                    >
                      {requestRefill.isPending ? "Requesting..." : "Request Refill"}
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <div className="text-center py-12">
            <Pill className="w-12 h-12 text-gray-400 mx-auto mb-4" aria-hidden="true" />
            <p className="text-base text-gray-600 mb-4">
              No prescriptions found.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
