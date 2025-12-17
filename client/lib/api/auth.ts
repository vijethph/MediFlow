import apiClient from "./client";

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  name: Array<{
    use?: string;
    family?: string;
    given?: string[];
    text?: string;
  }>;
  telecom?: Array<{
    system: string;
    value: string;
    use?: string;
  }>;
  email: string;
  password: string;
  gender?: string;
  birth_date?: string;
  address?: Array<{
    use?: string;
    type?: string;
    text?: string;
    line?: string[];
    city?: string;
    state?: string;
    postal_code?: string;
    country?: string;
  }>;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  patient_id: string;
  email: string;
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
    // Login endpoint is at /api/v1/patients/login (via Kong gateway)
    const response = await apiClient.post<TokenResponse>(
      "/api/v1/patients/login",
      credentials
    );
    
    // Store token
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", response.data.access_token);
      localStorage.setItem("patient_id", response.data.patient_id);
    }
    
    return response.data;
  },

  register: async (data: RegisterData): Promise<TokenResponse> => {
    // Register endpoint is at /api/v1/patients/register (via Kong gateway)
    const response = await apiClient.post<TokenResponse>(
      "/api/v1/patients/register",
      data
    );
    
    // Store token
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", response.data.access_token);
      localStorage.setItem("patient_id", response.data.patient_id);
    }
    
    return response.data;
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("patient_id");
    }
  },

  getToken: (): string | null => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("access_token");
    }
    return null;
  },

  refreshToken: async (): Promise<TokenResponse | null> => {
    // Token refresh logic - for now, just return null as backend doesn't have refresh endpoint
    // In production, you would call a refresh endpoint here
    const token = authApi.getToken();
    if (!token) {
      return null;
    }
    // For now, return null - implement refresh when backend supports it
    return null;
  },

  isTokenExpired: (): boolean => {
    const token = authApi.getToken();
    if (!token) {
      return true;
    }
    try {
      // Decode JWT token to check expiration
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      const payload = JSON.parse(jsonPayload);
      const exp = payload.exp * 1000; // Convert to milliseconds
      return Date.now() >= exp;
    } catch {
      return true;
    }
  },

  getPatientId: (): string | null => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("patient_id");
    }
    return null;
  },

  isAuthenticated: (): boolean => {
    return !!authApi.getToken();
  },

  changePassword: async (data: { currentPassword: string; newPassword: string }): Promise<void> => {
    // TODO: Implement password change endpoint when backend is ready
    // For now, this is a placeholder
    const response = await apiClient.post<void>("/api/v1/patients/change-password", data);
    return response.data;
  },
};
