"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Calendar, Clock, User, MapPin, Plus, Search } from "lucide-react";
import { useAppointments } from "@/lib/hooks/useAppointments";
import { authApi } from "@/lib/api/auth";

export default function AppointmentsPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  
  useEffect(() => {
    if (!authApi.isAuthenticated()) {
      router.replace("/login");
      return;
    }
  }, [router]);
  
  if (!authApi.isAuthenticated()) {
    return null;
  }

  const { data, isLoading, error } = useAppointments({
    appointment_status: statusFilter || undefined,
  });

  const appointments = data?.items || [];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "booked":
        return "confirmed";
      case "pending":
      case "proposed":
        return "pending";
      case "cancelled":
        return "cancelled";
      case "fulfilled":
        return "completed";
      default:
        return "pending";
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const filteredAppointments = appointments.filter((apt) => {
    // Status filtering - handle both pending and proposed as "pending"
    if (statusFilter) {
      if (statusFilter === "pending") {
        // If filtering for "pending", include both "pending" and "proposed"
        if (apt.status !== "pending" && apt.status !== "proposed") {
          return false;
        }
      } else if (apt.status !== statusFilter) {
        return false;
      }
    }
    
    // Search filtering
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesSearch = 
        apt.description?.toLowerCase().includes(query) ||
        apt.location?.toLowerCase().includes(query) ||
        apt.practitioner_id?.toLowerCase().includes(query);
      if (!matchesSearch) return false;
    }
    
    return true;
  });

  // Calculate pagination on filtered results
  const totalPages = Math.ceil(filteredAppointments.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;

  // Apply pagination
  const paginatedAppointments = filteredAppointments.slice(startIndex, endIndex);

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
        <ErrorMessage message="Failed to load appointments. Please try again." />
      </div>
    );
  }

  // Use a stable date reference to avoid hydration mismatches
  const today = new Date();
  const todayDateString = today.toDateString();
  
  // Calculate counts from the full appointments list (before filtering)
  const todayCount = appointments.filter(
    (apt) =>
      new Date(apt.start).toDateString() === todayDateString &&
      (apt.status === "booked" || apt.status === "pending" || apt.status === "proposed")
  ).length;

  const thisWeekCount = appointments.filter(
    (apt) => {
      const aptDate = new Date(apt.start);
      const weekFromNow = new Date(today);
      weekFromNow.setDate(today.getDate() + 7);
      return (
        aptDate >= today &&
        aptDate <= weekFromNow &&
        (apt.status === "booked" || apt.status === "pending" || apt.status === "proposed")
      );
    }
  ).length;

  // Count all pending-like statuses (pending, proposed)
  const pendingCount = appointments.filter(
    (apt) => apt.status === "pending" || apt.status === "proposed"
  ).length;

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">My Appointments</h1>
          <p className="text-base text-gray-600">Schedule and manage your appointments</p>
        </div>
        <Link href="/appointments/book">
          <Button variant="primary" className="mt-4 sm:mt-0">
            <Plus className="w-4 h-4" aria-hidden="true" />
            Schedule Appointment
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Today</p>
              <p className="text-3xl font-bold text-gray-900">{todayCount}</p>
            </div>
            <div className="p-4 bg-blue-100 rounded-xl">
              <Calendar className="w-8 h-8 text-blue-600" aria-hidden="true" />
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">This Week</p>
              <p className="text-3xl font-bold text-gray-900">{thisWeekCount}</p>
            </div>
            <div className="p-4 bg-blue-100 rounded-xl">
              <Calendar className="w-8 h-8 text-blue-600" aria-hidden="true" />
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Pending</p>
              <p className="text-3xl font-bold text-gray-900">{pendingCount}</p>
            </div>
            <div className="p-4 bg-yellow-100 rounded-xl">
              <Clock className="w-8 h-8 text-yellow-600" aria-hidden="true" />
            </div>
          </div>
        </Card>
      </div>

      {/* Search Bar */}
      <Card className="mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search 
              className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" 
              aria-hidden="true" 
            />
            <input
              type="text"
              placeholder="Search appointments..."
              className="input pl-10 w-full"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search appointments"
            />
          </div>
          <select
            className="input md:w-48 w-full md:w-auto"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
          >
            <option value="">All Status</option>
            <option value="booked">Confirmed</option>
            <option value="pending">Pending</option>
            <option value="proposed">Proposed</option>
            <option value="fulfilled">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </Card>

      {/* Appointments List */}
      {filteredAppointments.length > 0 ? (
        <div className="space-y-4">
          {filteredAppointments.map((appointment) => (
            <Card key={appointment.id} hoverable>
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    <div>
                      <p className="text-2xl font-bold text-gray-900">{formatDate(appointment.start)}</p>
                      <p className="text-lg text-gray-700">{formatTime(appointment.start)}</p>
                    </div>
                    <StatusBadge status={getStatusColor(appointment.status)}>
                      {appointment.status === "booked" ? "Confirmed" : 
                       appointment.status === "pending" || appointment.status === "proposed" ? "Pending Confirmation" :
                       appointment.status === "fulfilled" ? "Completed" :
                       appointment.status === "cancelled" ? "Cancelled" :
                       appointment.status}
                    </StatusBadge>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-base text-gray-600">
                    {appointment.practitioner_id && (
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-gray-400" aria-hidden="true" />
                        <span>Dr. {appointment.practitioner_id}</span>
                      </div>
                    )}
                    {appointment.location && (
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-gray-400" aria-hidden="true" />
                        <span>{appointment.location}</span>
                      </div>
                    )}
                  </div>
                  {appointment.description && (
                    <p className="text-sm text-gray-500 mt-2">{appointment.description}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <Link href={`/appointments/${appointment.id}`}>
                    <Button variant="secondary">View Details</Button>
                  </Link>
                  {(appointment.status === "pending" || appointment.status === "proposed") && (
                    <Link href={`/appointments/${appointment.id}/reschedule`}>
                      <Button variant="secondary">Reschedule</Button>
                    </Link>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <div className="text-center py-12">
            <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" aria-hidden="true" />
            <p className="text-base text-gray-600 mb-4">
              No appointments scheduled. Book your first appointment.
            </p>
            <Link href="/appointments/book">
              <Button variant="primary">Schedule Appointment</Button>
            </Link>
          </div>
        </Card>
      )}
    </div>
  );
}
