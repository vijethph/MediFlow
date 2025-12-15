import apiClient from "./client";

export interface Prescription {
  id: string;
  prescription_id: string;
  patient_id: string;
  doctor_name?: string;
  doctor_id?: string;
  medications: Array<{
    medication_name: string;
    dosage: string;
    frequency: string;
    duration_days: number;
    instructions?: string;
    quantity?: number;
  }>;
  diagnosis: string;
  notes?: string;
  status: "active" | "pending" | "expired" | "filled" | "cancelled";
  created_at?: string;
  updated_at?: string;
  // Computed fields for UI
  medication?: string; // First medication name
  dosage?: string; // First medication dosage
  quantity?: number; // First medication quantity
  start_date?: string; // Computed from created_at
  end_date?: string; // Computed from duration_days
  refills_remaining?: number; // Default to 0
}

export interface PrescriptionList {
  total: number;
  count: number;
  skip: number;
  limit: number;
  items: Prescription[];
}

export interface PrescriptionCreate {
  patient_id: string;
  doctor_name: string;
  doctor_id?: string;
  appointment_id?: string;
  medications: Array<{
    medication_name: string;
    dosage: string;
    frequency: string;
    duration_days: number;
    instructions?: string;
    quantity?: number;
  }>;
  diagnosis: string;
  notes?: string;
  lab_tests_ordered?: string[];
  follow_up_required?: boolean;
  follow_up_days?: number;
}

export const prescriptionsApi = {
  getPrescription: async (prescriptionId: string): Promise<Prescription> => {
    const response = await apiClient.get<Prescription>(
      `/api/v1/prescriptions/${prescriptionId}`
    );
    return response.data;
  },

  listPrescriptions: async (params?: {
    patient_id?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<PrescriptionList> => {
    // Backend requires patient_id as query parameter
    if (!params?.patient_id) {
      throw new Error("patient_id is required");
    }
    const response = await apiClient.get<any>("/api/v1/prescriptions", {
      params: {
        patient_id: params.patient_id,
        skip: params.skip || 0,
        limit: params.limit || 100,
      },
    });
    // Transform response to match our interface
    // Backend returns PrescriptionListResponse with 'prescriptions' field, not 'items'
    const data = response.data;
    const prescriptions = (data.prescriptions || data.items || []).map((p: any) => {
      const firstMed = p.medications?.[0];
      const createdDate = p.created_at ? new Date(p.created_at) : new Date();
      const endDate = firstMed?.duration_days 
        ? new Date(createdDate.getTime() + firstMed.duration_days * 24 * 60 * 60 * 1000)
        : createdDate;
      
      return {
        ...p,
        id: p.id || p._id || p.prescription_id,
        medication: firstMed?.medication_name || "Unknown",
        dosage: firstMed?.dosage || "",
        quantity: firstMed?.quantity || 0,
        start_date: createdDate.toISOString().split("T")[0],
        end_date: endDate.toISOString().split("T")[0],
        refills_remaining: 0, // Default, can be updated if backend provides
      };
    });
    
    return {
      total: data.total || prescriptions.length,
      count: prescriptions.length,
      skip: params.skip || 0,
      limit: params.limit || 100,
      items: prescriptions,
    };
  },

  createPrescription: async (data: PrescriptionCreate): Promise<Prescription> => {
    // Transform frontend format to backend format
    // Backend expects frequency as MedicationFrequency enum
    // Map frontend frequency strings to backend enum values
    const frequencyMap: Record<string, string> = {
      "once_daily": "once_daily",
      "twice_daily": "twice_daily",
      "three_times_daily": "three_times_daily",
      "four_times_daily": "four_times_daily",
      "as_needed": "as_needed",
      // Handle common variations
      "once a day": "once_daily",
      "twice a day": "twice_daily",
      "three times a day": "three_times_daily",
      "four times a day": "four_times_daily",
      "as needed": "as_needed",
    };
    
    const backendData = {
      ...data,
      medications: data.medications.map((med) => ({
        ...med,
        frequency: frequencyMap[med.frequency.toLowerCase()] || med.frequency,
      })),
    };
    
    const response = await apiClient.post<Prescription>("/api/v1/prescriptions", backendData);
    const responseData = response.data;
    
    // Transform backend response to frontend format
    const responseDataAny = responseData as any; // Type assertion for backend response
    return {
      ...responseData,
      id: responseData.id || responseDataAny._id || responseData.prescription_id || "",
      prescription_id: responseData.prescription_id || responseData.id || "",
    };
  },

  requestRefill: async (prescriptionId: string): Promise<Prescription> => {
    // Update prescription status to pending for refill
    const response = await apiClient.put<Prescription>(
      `/api/v1/prescriptions/${prescriptionId}`,
      { status: "pending" }
    );
    return response.data;
  },
};
