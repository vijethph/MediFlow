"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useCreateAppointment } from "@/lib/hooks/useAppointments";
import { authApi } from "@/lib/api/auth";
import { appointmentBookingSchema, type AppointmentBookingFormData } from "@/lib/validations";
import { useNotificationContext } from "@/components/providers/NotificationProvider";
import { Calendar, Clock, MapPin, User } from "lucide-react";

export default function BookAppointmentPage() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const createAppointment = useCreateAppointment();
  const { success, error: showError } = useNotificationContext();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
    setError: setFormError,
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

  if (isChecking || !isAuthenticated) {
    return null;
  }

  const onSubmit = async (data: AppointmentBookingFormData) => {
    try {
      const patientId = authApi.getPatientId();
      if (!patientId) {
        setFormError("root", { message: "Patient ID not found. Please log in again." });
        return;
      }

      // Calculate end time based on start time and duration
      const start = new Date(data.start);
      const durationMinutes = parseInt(data.duration, 10);
      const end = new Date(start.getTime() + durationMinutes * 60 * 1000);

      await createAppointment.mutateAsync({
        patient_id: patientId,
        practitioner_name: data.practitioner_name,
        practitioner_id: data.practitioner_id,
        start: start.toISOString(),
        end: end.toISOString(),
        description: data.description,
        location: data.location,
        service_type: data.service_type,
        specialty: data.specialty,
        appointment_type: data.appointment_type,
        comment: data.comment,
      });

      success("Appointment Booked", "Your appointment has been successfully scheduled.");
      router.push("/appointments");
      router.refresh();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to book appointment. Please try again.";
      setFormError("root", { message: errorMessage });
      showError("Booking Failed", errorMessage);
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
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Book New Appointment</h1>
        <p className="text-gray-600">Schedule an appointment with a healthcare provider</p>
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
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Input
                label="Start Date & Time"
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
            <label htmlFor="appointment_type" className="label">
              Appointment Type
            </label>
            <select
              id="appointment_type"
              className="input"
              {...register("appointment_type")}
            >
              <option value="consultation">Consultation</option>
              <option value="follow-up">Follow-up</option>
              <option value="emergency">Emergency</option>
              <option value="routine">Routine</option>
            </select>
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
                  Booking...
                </>
              ) : (
                <>
                  <Calendar className="w-4 h-4" />
                  Book Appointment
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
