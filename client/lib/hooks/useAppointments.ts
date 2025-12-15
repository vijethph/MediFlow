import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { appointmentsApi, Appointment, AppointmentCreate, AppointmentUpdate } from "@/lib/api/appointments";
import { authApi } from "@/lib/api/auth";
import { handleApiError } from "@/lib/api/client";

export function useAppointments(filters?: {
  patient_id?: string;
  appointment_status?: string;
  start_date?: string;
  end_date?: string;
}) {
  const [patientId, setPatientId] = useState<string | null>(null);
  
  useEffect(() => {
    setPatientId(authApi.getPatientId());
  }, []);
  
  return useQuery({
    queryKey: ["appointments", filters, patientId],
    queryFn: () => {
      if (!patientId) {
        throw new Error("Patient ID is required");
      }
      return appointmentsApi.listAppointments({
        patient_id: patientId,
        appointment_status: filters?.appointment_status,
        start_date: filters?.start_date,
        end_date: filters?.end_date,
      });
    },
    enabled: !!patientId,
  });
}

export function useAppointment(appointmentId: string) {
  return useQuery({
    queryKey: ["appointment", appointmentId],
    queryFn: () => appointmentsApi.getAppointment(appointmentId),
    enabled: !!appointmentId,
  });
}

export function useCreateAppointment() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: AppointmentCreate) => appointmentsApi.createAppointment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
    },
    onError: (error) => {
      throw handleApiError(error);
    },
  });
}

export function useUpdateAppointment() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AppointmentUpdate }) =>
      appointmentsApi.updateAppointment(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
    },
    onError: (error) => {
      throw handleApiError(error);
    },
  });
}

export function useCancelAppointment() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (appointmentId: string) => appointmentsApi.cancelAppointment(appointmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
    },
    onError: (error) => {
      throw handleApiError(error);
    },
  });
}
