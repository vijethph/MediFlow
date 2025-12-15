import apiClient from "./client";

export interface Patient {
  id?: string | number;
  patient_id: string;
  full_name?: string;
  name?: Array<{ given: string[]; family: string }>;
  email?: string;
  phone?: string;
  date_of_birth?: string;
  birth_date?: string;
  gender?: string;
  address?: string;
  allergies?: string;
  medical_history?: string;
  current_medications?: string;
  blood_group?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  is_active?: boolean;
  active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface PatientList {
  total: number;
  count: number;
  skip: number;
  limit: number;
  items: Patient[];
}

export const patientsApi = {
  getPatient: async (patientId: string): Promise<Patient> => {
    const response = await apiClient.get<any>(`/api/v1/patients/${patientId}`);
    const data = response.data;
    // Transform backend response to match our interface
    return {
      ...data,
      id: data.id || data.patient_id,
      active: data.is_active ?? data.active ?? true,
      birth_date: data.date_of_birth || data.birth_date,
      // If backend returns full_name, create name array for compatibility
      name: data.name || (data.full_name ? [{
        given: data.full_name.split(" ").slice(0, -1),
        family: data.full_name.split(" ").slice(-1)[0] || ""
      }] : []),
    };
  },

  listPatients: async (skip = 0, limit = 100): Promise<PatientList> => {
    const response = await apiClient.get<PatientList>("/api/v1/patients", {
      params: { skip, limit },
    });
    return response.data;
  },

  updatePatient: async (patientId: string, data: Partial<Patient>): Promise<Patient> => {
    const response = await apiClient.put<Patient>(`/api/v1/patients/${patientId}`, data);
    return response.data;
  },
};
