import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { prescriptionsApi, Prescription, PrescriptionCreate } from "@/lib/api/prescriptions";
import { authApi } from "@/lib/api/auth";
import { handleApiError } from "@/lib/api/client";

export function usePrescriptions(filters?: { status?: string }) {
  const [patientId, setPatientId] = useState<string | null>(null);
  
  useEffect(() => {
    setPatientId(authApi.getPatientId());
  }, []);
  
  return useQuery({
    queryKey: ["prescriptions", filters, patientId],
    queryFn: () => {
      if (!patientId) {
        throw new Error("Patient ID is required");
      }
      return prescriptionsApi.listPrescriptions({
        patient_id: patientId,
        ...filters,
      });
    },
    enabled: !!patientId,
  });
}

export function usePrescription(prescriptionId: string) {
  return useQuery({
    queryKey: ["prescription", prescriptionId],
    queryFn: () => prescriptionsApi.getPrescription(prescriptionId),
    enabled: !!prescriptionId,
  });
}

export function useCreatePrescription() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: PrescriptionCreate) => prescriptionsApi.createPrescription(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prescriptions"] });
    },
    onError: (error) => {
      throw handleApiError(error);
    },
  });
}

export function useRequestRefill() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (prescriptionId: string) => prescriptionsApi.requestRefill(prescriptionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prescriptions"] });
    },
    onError: (error) => {
      throw handleApiError(error);
    },
  });
}
