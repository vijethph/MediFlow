import apiClient from "./client";

export interface AppointmentParticipant {
  type?: string[];
  actor?: string;
  status: string;
}

export interface Appointment {
  id: string;
  patient_id: string;
  practitioner_id?: string;
  status: "proposed" | "pending" | "booked" | "arrived" | "fulfilled" | "cancelled" | "noshow";
  start: string;
  end: string;
  description?: string;
  location?: string;
  participants?: AppointmentParticipant[];
  created_at?: string;
  updated_at?: string;
}

export interface AppointmentList {
  total: number;
  count: number;
  skip: number;
  limit: number;
  items: Appointment[];
}

export interface AppointmentCreate {
  patient_id: string;
  practitioner_name?: string;
  practitioner_id?: string;
  start: string; // ISO datetime string
  end: string; // ISO datetime string
  status?: "proposed" | "pending" | "booked";
  description?: string;
  location?: string;
  service_type?: string;
  specialty?: string;
  appointment_type?: string;
  comment?: string;
}

export interface AppointmentUpdate {
  start?: string;
  end?: string;
  status?: string;
  description?: string;
  location?: string;
}

export const appointmentsApi = {
  getAppointment: async (appointmentId: string): Promise<Appointment> => {
    const response = await apiClient.get<any>(
      `/api/v1/appointments/${appointmentId}`
    );
    const data = response.data;
    
    // Transform backend format to frontend format
    // Backend returns FHIR R4 format with start/end (or appointment_date/end_time for other service)
    const appointment: Appointment = {
      ...data,
      id: data.id || data.appointment_id || "",
      start: data.start || data.appointment_date || "",
      end: data.end || data.end_time || "",
      patient_id: data.participant?.[0]?.actor || data.patient_id || "",
      practitioner_id: data.participant?.[1]?.actor || data.practitioner_id || "",
      status: data.status || "proposed",
      description: data.description || "",
      location: data.location || "",
    };
    
    return appointment;
  },

  listAppointments: async (params?: {
    patient_id?: string;
    practitioner_id?: string;
    appointment_status?: string;
    start_date?: string;
    end_date?: string;
    skip?: number;
    limit?: number;
  }): Promise<AppointmentList> => {
    // Backend requires patient_id, so ensure it's included
    if (!params?.patient_id) {
      throw new Error("patient_id is required to list appointments");
    }
    
    // Transform frontend params to backend format
    const backendParams: any = {
      skip: params.skip || 0,
      limit: params.limit || 100,
      patient_id: params.patient_id, // Add patient_id as query parameter
    };
    
    // Backend uses 'appointment_status' not 'status', and 'start_date'/'end_date' (FHIR R4 compatible)
    if (params.appointment_status) {
      backendParams.appointment_status = params.appointment_status;
    }
    if (params.start_date) {
      backendParams.start_date = params.start_date;
    }
    if (params.end_date) {
      backendParams.end_date = params.end_date;
    }
    
    // Use list endpoint with patient_id query parameter (more reliable than path parameter)
    const response = await apiClient.get<any>(`/api/v1/appointments`, {
      params: backendParams,
    });
    
    // Transform backend response to frontend format
    const data = response.data;
    const appointments = Array.isArray(data) ? data : data.items || [];
    
    const transformedAppointments = appointments.map((apt: any) => ({
      ...apt,
      id: apt.id || apt.appointment_id || "",
      start: apt.start || apt.appointment_date || "",
      end: apt.end || apt.end_time || "",
      patient_id: apt.participant?.[0]?.actor || apt.patient_id || "",
      practitioner_id: apt.participant?.[1]?.actor || apt.practitioner_id || "",
      status: apt.status || "proposed",
      description: apt.description || "",
      location: apt.location || "",
    }));
    
    return {
      total: data.total || transformedAppointments.length,
      count: transformedAppointments.length,
      skip: params.skip || 0,
      limit: params.limit || 100,
      items: transformedAppointments,
    };
  },

  createAppointment: async (data: AppointmentCreate): Promise<Appointment> => {
    // Calculate end time based on start time and duration
    const start = new Date(data.start);
    const end = new Date(data.end);
    
    // Transform to backend schema (FHIR R4 compatible - uses start/end)
    // The Docker service uses local/healthcare-system/services/appointment-service schema
    const backendData = {
      patient_id: data.patient_id,
      practitioner_name: data.practitioner_name || "Unknown Doctor",
      practitioner_id: data.practitioner_id || data.practitioner_name || "DOCTOR-001",
      start: start.toISOString(),
      end: end.toISOString(),
      description: data.description || "",
      comment: data.comment || "",
      location: data.location || "",
      service_type: data.service_type || "",
      specialty: data.specialty || "",
      appointment_type: data.appointment_type || "consultation",
      status: data.status || "proposed",
    };
    
    const response = await apiClient.post<any>("/api/v1/appointments", backendData);
    const responseData = response.data;
    
    // Transform backend response to frontend format
    // Backend returns FHIR R4 format with start/end
    return {
      ...responseData,
      id: responseData.id || responseData.appointment_id || "",
      start: responseData.start || "",
      end: responseData.end || "",
      patient_id: responseData.participant?.[0]?.actor || data.patient_id,
      practitioner_id: responseData.participant?.[1]?.actor || data.practitioner_id,
      status: responseData.status || "proposed",
      description: responseData.description || "",
      location: responseData.location || "",
    };
  },

  updateAppointment: async (
    appointmentId: string,
    data: AppointmentUpdate
  ): Promise<Appointment> => {
    // Transform frontend format to backend format (FHIR R4 uses start/end)
    const backendData: any = {};
    
    if (data.start) {
      backendData.start = new Date(data.start).toISOString();
    }
    if (data.end) {
      backendData.end = new Date(data.end).toISOString();
    }
    if (data.status) {
      backendData.status = data.status;
    }
    if (data.description !== undefined) {
      backendData.description = data.description;
    }
    if (data.location !== undefined) {
      backendData.location = data.location;
    }
    
    const response = await apiClient.put<any>(
      `/api/v1/appointments/${appointmentId}`,
      backendData
    );
    const responseData = response.data;
    
    // Transform backend response to frontend format
    return {
      ...responseData,
      id: responseData.id || responseData.appointment_id || "",
      start: responseData.start || "",
      end: responseData.end || "",
      patient_id: responseData.participant?.[0]?.actor || responseData.patient_id || "",
      practitioner_id: responseData.participant?.[1]?.actor || responseData.practitioner_id || "",
      status: responseData.status || "proposed",
      description: responseData.description || "",
      location: responseData.location || "",
    };
  },

  cancelAppointment: async (appointmentId: string): Promise<Appointment> => {
    const response = await apiClient.post<any>(
      `/api/v1/appointments/${appointmentId}/cancel`
    );
    const responseData = response.data;
    
    // Transform backend response to frontend format
    return {
      ...responseData,
      id: responseData.id || responseData.appointment_id || "",
      start: responseData.start || responseData.appointment_date || "",
      end: responseData.end || responseData.end_time || "",
      patient_id: responseData.participant?.[0]?.actor || responseData.patient_id || "",
      practitioner_id: responseData.participant?.[1]?.actor || responseData.practitioner_id || "",
      status: responseData.status || "cancelled",
      description: responseData.description || "",
      location: responseData.location || "",
    };
  },

  deleteAppointment: async (appointmentId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/appointments/${appointmentId}`);
  },
};
