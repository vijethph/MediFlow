"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useAppointment, useUpdateAppointment } from "@/lib/hooks/useAppointments";
import { authApi } from "@/lib/api/auth";
import { appointmentBookingSchema, type AppointmentBookingFormData } from "@/lib/validations";
import { useNotificationContext } from "@/components/providers/NotificationProvider";
import { Calendar, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function RescheduleAppointmentPage() {
  const router = useRouter();
  const params = useParams();
  const appointmentId = params?.id as string;
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const { data: appointment, isLoading: isLoadingAppointment } = useAppointment(appointmentId || "");
  const updateAppointment = useUpdateAppointment();
  const { success, error: showError } = useNotificationContext();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
    setError: setFormError,
    reset,
  } = useForm<AppointmentBookingFormData>({
    resolver: zodResolver(appointmentBookingSchema),
    defaultValues: {
      appointment_type: "consultation",
      duration: "30",
    },
  });
  
  const startTime = watch("start");
  const duration = watch("duration");

  useEffect(() => {
    const authenticated = authApi.isAuthenticated();
    setIsAuthenticated(authenticated);
    setIsChecking(false);
    if (!authenticated) {
      router.replace("/login");
    }
  }, [router]);

  // Pre-fill form when appointment data is loaded
  useEffect(() => {
    if (appointment) {
      const start = new Date(appointment.start);
      const end = new Date(appointment.end);
      const durationMinutes = Math.round((end.getTime() - start.getTime()) / (1000 * 60));
      
      // Format datetime-local input (YYYY-MM-DDTHH:mm)
      const year = start.getFullYear();
      const month = String(start.getMonth() + 1).padStart(2, "0");
      const day = String(start.getDate()).padStart(2, "0");
      const hours = String(start.getHours()).padStart(2, "0");
      const minutes = String(start.getMinutes()).padStart(2, "0");
      const datetimeLocal = `${year}-${month}-${day}T${hours}:${minutes}`;
      
      reset({
        practitioner_name: appointment.practitioner_id || "Dr. Unknown",
        start: datetimeLocal,
        duration: durationMinutes === 60 ? "60" : "30",
        description: appointment.description || "",
        location: appointment.location || "",
      });
    }
  }, [appointment, reset]);

  if (isChecking || !isAuthenticated) {
    return null;
  }

  if (isLoadingAppointment) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (!appointment) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="text-center py-12">
          <p className="text-base text-gray-600 mb-4">Appointment not found</p>
          <Link href="/appointments">
            <Button variant="primary">Back to Appointments</Button>
          </Link>
        </div>
      </div>
    );
  }

  const onSubmit = async (data: AppointmentBookingFormData) => {
    try {
      // Calculate end time based on start time and duration
      const start = new Date(data.start);
      const durationMinutes = parseInt(data.duration, 10);
      const end = new Date(start.getTime() + durationMinutes * 60 * 1000);

      // Use appointment.id if available, otherwise use appointmentId from params
      const idToUpdate = appointment.id || appointmentId;
      
      await updateAppointment.mutateAsync({
        id: idToUpdate,
        data: {
          start: start.toISOString(),
          end: end.toISOString(),
          description: data.description,
          location: data.location,
        },
      });

      success("Appointment Rescheduled", "Your appointment has been successfully rescheduled.");
      router.push(`/appointments/${appointment.id || appointmentId}`);
      router.refresh();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to reschedule appointment. Please try again.";
      setFormError("root", { message: errorMessage });
      showError("Reschedule Failed", errorMessage);
    }
  };
  
  // Get minimum datetime (current time)
  const getMinDateTime = () => {
    const now = new Date();
    // Add 1 minute buffer to ensure we're always in the future
    now.setMinutes(now.getMinutes() + 1);
    // Format as YYYY-MM-DDTHH:mm for datetime-local input
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <Link href={`/appointments/${appointmentId}`}>
        <Button variant="outline" className="mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Appointment
        </Button>
      </Link>

      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Reschedule Appointment</h1>
        <p className="text-gray-600">Update the date and time for your appointment</p>
      </div>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {errors.root && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{errors.root.message}</p>
            </div>
          )}

          <div>
            <Input
              label="Practitioner Name"
              required
              {...register("practitioner_name")}
              error={errors.practitioner_name?.message}
              placeholder="Dr. John Smith"
              disabled
            />
            <p className="text-xs text-gray-500 mt-1">Practitioner cannot be changed when rescheduling</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Input
                label="New Start Date & Time"
                type="datetime-local"
                required
                {...register("start")}
                error={errors.start?.message}
                min={getMinDateTime()}
              />
            </div>
            <div>
              <label htmlFor="duration" className="label">
                Appointment Duration <span className="text-red-500">*</span>
              </label>
              <select
                id="duration"
                className="input"
                {...register("duration")}
              >
                <option value="30">30 minutes</option>
                <option value="60">60 minutes</option>
              </select>
              {errors.duration && (
                <p className="text-sm text-red-600 mt-1">{errors.duration.message}</p>
              )}
              {startTime && duration && (
                <p className="text-xs text-gray-500 mt-1">
                  End time: {(() => {
                    const start = new Date(startTime);
                    const durationMinutes = parseInt(duration, 10);
                    const end = new Date(start.getTime() + durationMinutes * 60 * 1000);
                    return end.toLocaleString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                      hour: "numeric",
                      minute: "2-digit",
                    });
                  })()}
                </p>
              )}
            </div>
          </div>

          <div>
            <Input
              label="Location (Optional)"
              {...register("location")}
              error={errors.location?.message}
              placeholder="Clinic Room 101"
            />
          </div>

          <div>
            <label htmlFor="description" className="label">
              Description (Optional)
            </label>
            <textarea
              id="description"
              className="input min-h-[100px]"
              {...register("description")}
              placeholder="Brief description of the appointment reason"
            />
          </div>

          <div className="flex gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.back()}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? (
                <>
                  <LoadingSpinner size="sm" />
                  Rescheduling...
                </>
              ) : (
                <>
                  <Calendar className="w-4 h-4" />
                  Reschedule Appointment
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
