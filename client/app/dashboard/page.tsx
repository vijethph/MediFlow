"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Calendar, AlertCircle, Clock, CheckCircle } from "lucide-react";
import { useAppointments } from "@/lib/hooks/useAppointments";
import { usePrescriptions } from "@/lib/hooks/usePrescriptions";
import { useInvoices } from "@/lib/hooks/useBilling";
import { usePatient } from "@/lib/hooks/usePatient";
import { authApi } from "@/lib/api/auth";

export default function DashboardPage() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  
  // Always call hooks at the top - never conditionally
  const { data: patient, isLoading: patientLoading, error: patientError } = usePatient();
  const { data: appointmentsData, isLoading: appointmentsLoading, error: appointmentsError } = useAppointments();
  const { data: prescriptionsData, isLoading: prescriptionsLoading, error: prescriptionsError } = usePrescriptions();
  const { data: invoicesData, isLoading: invoicesLoading, error: invoicesError } = useInvoices();
  
  useEffect(() => {
    const authenticated = authApi.isAuthenticated();
    setIsAuthenticated(authenticated);
    setIsChecking(false);
    
    if (!authenticated) {
      router.replace("/login");
      return;
    }
  }, [router]);
  
  // Don't render if not authenticated or still checking
  if (isChecking || !isAuthenticated) {
    return null;
  }

  const greeting = "Good morning"; // TODO: Dynamic based on time
  const userName = patient?.full_name 
    ? patient.full_name
    : patient?.name?.[0] 
    ? `${patient.name[0].given?.join(" ") || ""} ${patient.name[0].family || ""}`.trim()
    : "User";

  // Get next appointment (handle errors gracefully)
  // Filter for upcoming appointments (future dates) with status booked, pending, or proposed
  const now = new Date();
  const nextAppointment = !appointmentsError && appointmentsData?.items
    ?.filter((apt) => {
      const aptDate = new Date(apt.start);
      const isUpcoming = aptDate >= now;
      const isActiveStatus = apt.status === "booked" || apt.status === "pending" || apt.status === "proposed";
      return isUpcoming && isActiveStatus;
    })
    .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())[0];

  // Get pending prescriptions (handle errors gracefully)
  const pendingPrescriptions = !prescriptionsError && prescriptionsData?.items?.filter(
    (p) => p.status === "pending" || (p.refills_remaining !== undefined && p.refills_remaining === 0)
  ) || [];

  // Get pending invoices (handle errors gracefully)
  const pendingInvoices = !invoicesError && invoicesData?.items?.filter(
    (inv) => inv.status === "issued" || inv.status === "balanced"
  ) || [];

  const pendingActions = [
    ...pendingPrescriptions.slice(0, 1).map((p) => ({
      type: "prescription" as const,
      message: `Prescription refill pending: ${p.medication}`,
      status: "pending" as const,
    })),
    ...pendingInvoices.slice(0, 1).map((inv) => {
      const dueDate = inv.due_date || inv.date;
      let formattedDate = "N/A";
      if (dueDate) {
        try {
          const date = new Date(dueDate);
          const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
          const month = monthNames[date.getMonth()];
          const day = date.getDate();
          formattedDate = `${month} ${day}`;
        } catch {
          formattedDate = "N/A";
        }
      }
      return {
        type: "invoice" as const,
        message: `Invoice due by ${formattedDate}`,
        status: "urgent" as const,
      };
    }),
  ];

  const stats = {
    upcomingAppointments: !appointmentsError && appointmentsData?.items?.filter(
      (apt) => {
        const aptDate = new Date(apt.start);
        const now = new Date();
        const isUpcoming = aptDate >= now;
        const isActiveStatus = apt.status === "booked" || apt.status === "pending" || apt.status === "proposed";
        return isUpcoming && isActiveStatus;
      }
    ).length || 0,
    activePrescriptions: !prescriptionsError && prescriptionsData?.items?.filter(
      (p) => p.status === "active"
    ).length || 0,
    outstandingBalance: !invoicesError && invoicesData?.items
      ?.filter((inv) => inv.status === "issued" || inv.status === "balanced")
      .reduce((sum, inv) => sum + (inv.amount_due || 0), 0) || 0,
  };

  // Format dates consistently to avoid hydration mismatches
  // Use a stable format that doesn't depend on locale/timezone differences
  const formatDateTime = (dateString: string) => {
    if (!dateString) return "N/A";
    try {
      const date = new Date(dateString);
      // Extract components directly to avoid locale-specific formatting
      const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const month = monthNames[date.getMonth()];
      const day = date.getDate();
      const year = date.getFullYear();
      const hour = date.getHours() % 12 || 12;
      const minute = date.getMinutes().toString().padStart(2, "0");
      const ampm = date.getHours() >= 12 ? "PM" : "AM";
      return `${month} ${day}, ${year} ${hour}:${minute} ${ampm}`;
    } catch {
      return "Invalid date";
    }
  };

  const isLoading = patientLoading || appointmentsLoading || prescriptionsLoading || invoicesLoading;
  
  // Show partial data even if some APIs fail - only show error if critical data fails
  const criticalError = patientError; // Patient data is critical
  const hasNonCriticalErrors = appointmentsError || prescriptionsError || invoicesError;
  
  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (criticalError) {
    const errorMessage = criticalError?.message || "Failed to load dashboard data. Please try again.";
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-8">
        <ErrorMessage message={errorMessage} />
        <div className="mt-4">
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    );
  }
  
  // Show warning if some APIs failed but we can still show partial data
  const warningMessage = hasNonCriticalErrors 
    ? (appointmentsError?.message || prescriptionsError?.message || invoicesError?.message || "Some data may be unavailable")
    : null;

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8">
      {/* FHIR R4 Compatibility Badge */}
      <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-2">
        <span className="text-sm font-semibold text-blue-900">FHIR R4 Compatible:</span>
        <span className="text-xs text-blue-700">All data models and APIs follow HL7 FHIR R4 standards</span>
      </div>
      {warningMessage && (
        <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-sm text-yellow-800">{warningMessage}</p>
        </div>
      )}
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        {greeting}, {userName}
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* Card 1: Next Appointment */}
        <Card className="md:col-span-2">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Your Next Appointment</h2>
          {nextAppointment ? (
            <div>
              <div className="flex items-start gap-4 mb-4">
                <div className="flex-1">
                  <p className="text-base font-semibold text-gray-700 mb-1">
                    {formatDateTime(nextAppointment.start)}
                  </p>
                  <p className="text-base text-gray-600 mb-1">
                    {nextAppointment.practitioner_id || "Doctor"}
                  </p>
                  <p className="text-sm text-gray-500">
                    {nextAppointment.description || "Appointment"}
                  </p>
                  {nextAppointment.location && (
                    <p className="text-sm text-gray-500">
                      {nextAppointment.location}
                    </p>
                  )}
                </div>
              </div>
              <Link href="/appointments">
                <Button variant="primary">Appointment Details</Button>
              </Link>
            </div>
          ) : (
            <div>
              <p className="text-base text-gray-600 mb-4">
                No upcoming appointments scheduled.
              </p>
              <Link href="/appointments/book">
                <Button variant="primary">Schedule Your First Appointment</Button>
              </Link>
            </div>
          )}
        </Card>

        {/* Card 2: Pending Actions */}
        <Card>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Pending Actions</h2>
          {pendingActions.length > 0 ? (
            <div>
              <p className="text-base text-gray-600 mb-4">
                You have {pendingActions.length} items requiring attention
              </p>
              <ul className="space-y-3" role="list">
                {pendingActions.map((action, index) => (
                  <li key={index}>
                    <Link
                      href={
                        action.type === "prescription"
                          ? "/prescriptions"
                          : "/billing"
                      }
                      className="flex items-start gap-2 text-base text-gray-700 hover:text-primary transition-colors"
                    >
                      <AlertCircle
                        className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
                          action.status === "urgent"
                            ? "text-danger"
                            : "text-warning"
                        }`}
                        aria-hidden="true"
                      />
                      <span>{action.message}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-base text-gray-500">All caught up!</p>
          )}
        </Card>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Card>
          <div className="text-center">
            <p className="text-sm text-gray-500 mb-2">
              Upcoming Appointments
            </p>
            <p className="text-4xl font-bold text-primary">
              {stats.upcomingAppointments}
            </p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-sm text-gray-500 mb-2">
              Active Prescriptions
            </p>
            <p className="text-4xl font-bold text-primary">
              {stats.activePrescriptions}
            </p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-sm text-gray-500 mb-2">
              Outstanding Balance
            </p>
            <p className="text-4xl font-bold text-danger">
              €{stats.outstandingBalance.toFixed(2)}
            </p>
          </div>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <h2 className="text-2xl font-semibold text-gray-900 mb-4">Recent Activity</h2>
        <ul className="space-y-3" role="list">
          {!appointmentsError && appointmentsData?.items
            ?.filter((apt) => apt.status === "fulfilled")
            .slice(0, 3)
            .map((apt) => (
              <li key={apt.id} className="flex items-center gap-3 text-base text-gray-600">
                <Clock className="w-4 h-4 text-gray-400" aria-hidden="true" />
                <span>
                  {formatDateTime(apt.start).split(",")[0]}: 
                  Appointment completed
                </span>
              </li>
            ))}
          {!prescriptionsError && prescriptionsData?.items
            ?.filter((p) => p.status === "filled")
            .slice(0, 2)
            .map((p) => (
              <li key={p.id} className="flex items-center gap-3 text-base text-gray-600">
                <CheckCircle className="w-4 h-4 text-success" aria-hidden="true" />
                <span>
                  {(p.updated_at || p.created_at) ? formatDateTime(p.updated_at || p.created_at || "").split(",")[0] : "N/A"}: 
                  Prescription filled: {p.medication}
                </span>
              </li>
            ))}
          {appointmentsError && prescriptionsError && (
            <li className="text-sm text-gray-500">No recent activity available</li>
          )}
        </ul>
      </Card>
    </div>
  );
}
