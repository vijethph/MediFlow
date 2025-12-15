"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAppointment } from "@/lib/hooks/useAppointments";
import { authApi } from "@/lib/api/auth";
import { Calendar, Clock, MapPin, User, ArrowLeft } from "lucide-react";

export default function AppointmentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const appointmentId = params?.id as string;
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  const { data: appointment, isLoading, error } = useAppointment(appointmentId || "");

  useEffect(() => {
    const authenticated = authApi.isAuthenticated();
    setIsAuthenticated(authenticated);
    setIsChecking(false);
    if (!authenticated) {
      router.replace("/login");
    }
  }, [router]);

  if (isChecking || !isAuthenticated) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (error || !appointment) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <ErrorMessage message={error?.message || "Appointment not found"} />
        <div className="mt-4">
          <Link href="/appointments">
            <Button variant="primary">Back to Appointments</Button>
          </Link>
        </div>
      </div>
    );
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    });
  };

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

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <Link href="/appointments">
        <Button variant="outline" className="mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Appointments
        </Button>
      </Link>

      <Card>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">Appointment Details</h1>
            <StatusBadge status={getStatusColor(appointment.status)}>
              {appointment.status === "booked" ? "Confirmed" : 
               appointment.status === "pending" || appointment.status === "proposed" ? "Pending Confirmation" :
               appointment.status === "fulfilled" ? "Completed" :
               appointment.status === "cancelled" ? "Cancelled" :
               appointment.status}
            </StatusBadge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex items-start gap-3">
              <Calendar className="w-5 h-5 text-gray-400 mt-1" />
              <div>
                <p className="text-sm text-gray-600">Date</p>
                <p className="text-lg font-semibold text-gray-900">{formatDate(appointment.start)}</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Clock className="w-5 h-5 text-gray-400 mt-1" />
              <div>
                <p className="text-sm text-gray-600">Time</p>
                <p className="text-lg font-semibold text-gray-900">
                  {formatTime(appointment.start)} - {formatTime(appointment.end)}
                </p>
              </div>
            </div>

            {appointment.practitioner_id && (
              <div className="flex items-start gap-3">
                <User className="w-5 h-5 text-gray-400 mt-1" />
                <div>
                  <p className="text-sm text-gray-600">Practitioner</p>
                  <p className="text-lg font-semibold text-gray-900">Dr. {appointment.practitioner_id}</p>
                </div>
              </div>
            )}

            {appointment.location && (
              <div className="flex items-start gap-3">
                <MapPin className="w-5 h-5 text-gray-400 mt-1" />
                <div>
                  <p className="text-sm text-gray-600">Location</p>
                  <p className="text-lg font-semibold text-gray-900">{appointment.location}</p>
                </div>
              </div>
            )}
          </div>

          {appointment.description && (
            <div>
              <p className="text-sm text-gray-600 mb-2">Description</p>
              <p className="text-base text-gray-900">{appointment.description}</p>
            </div>
          )}

          <div className="flex gap-4 pt-4 border-t border-gray-200">
            <Link href="/appointments">
              <Button variant="outline">Back</Button>
            </Link>
            {(appointment.status === "pending" || appointment.status === "proposed") && (
              <Link href={`/appointments/${appointment.id}/reschedule`}>
                <Button variant="secondary">Reschedule</Button>
              </Link>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
