import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { patientsApi, Patient } from "@/lib/api/patients";
import { authApi } from "@/lib/api/auth";
import { handleApiError } from "@/lib/api/client";

export function usePatient(patientId?: string) {
  const [id, setId] = useState<string | undefined>(patientId);
  
  useEffect(() => {
    if (!patientId) {
      setId(authApi.getPatientId() || undefined);
    }
  }, [patientId]);
  
  return useQuery({
    queryKey: ["patient", id],
    queryFn: () => patientsApi.getPatient(id!),
    enabled: !!id,
  });
}

export function useUpdatePatient() {
  const queryClient = useQueryClient();
  const patientId = authApi.getPatientId();
  
  return useMutation({
    mutationFn: (data: Partial<Patient>) => patientsApi.updatePatient(patientId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patient", patientId] });
    },
    onError: (error) => {
      throw handleApiError(error);
    },
  });
}
