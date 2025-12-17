import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from "axios";

// API Base URL - Kong Gateway (Note: This frontend runs on port 3001)
const API_BASE_URL = 
  process.env.NEXT_PUBLIC_API_URL || 
  (typeof window !== "undefined" ? window.location.origin.replace(":3001", ":8000") : "http://localhost:8000");

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
  maxRedirects: 5, // Follow redirects automatically
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get token from localStorage (or cookies in production)
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    // Check if response looks like a health check/root endpoint response instead of expected data
    // This happens when Kong routes incorrectly to the root endpoint
    if (response.data && typeof response.data === 'object' && 'service' in response.data && 'status' in response.data && !('items' in response.data || 'total' in response.data || 'data' in response.data)) {
      // This is a misrouted request - convert to error to trigger retry logic
      const error: any = new Error("API returned unexpected response format. The request may have been misrouted.");
      error.response = {
        status: 500,
        data: response.data,
        headers: response.headers,
      };
      error.config = response.config;
      return Promise.reject(error);
    }
    return response;
  },
  async (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status;
      
      // Handle 307 redirects - FastAPI redirects /appointments to /appointments/
      if (status === 307) {
        const originalUrl = error.config?.url || "";
        const originalParams = error.config?.params || {};
        // If redirecting to add trailing slash, retry with trailing slash and preserve params
        if (originalUrl && !originalUrl.endsWith("/")) {
          const queryString = new URLSearchParams(originalParams as Record<string, string>).toString();
          const retryUrl = originalUrl + "/" + (queryString ? "?" + queryString : "");
          return apiClient.get(retryUrl);
        }
        // Otherwise, follow the redirect location (but fix internal URLs)
        const location = error.response.headers.location;
        if (location) {
          // Replace internal service URLs with Kong gateway URL
          const fixedLocation = location.replace(/http:\/\/[^\/]+:800\d/, API_BASE_URL);
          return apiClient.get(fixedLocation);
        }
      }
      
      // Handle 500 errors that might be misrouted requests (root endpoint responses)
      if (status === 500 && error.response.data && typeof error.response.data === 'object' && 'service' in error.response.data) {
        // This is a misrouted request - try with different URL format
        const originalUrl = error.config?.url || "";
        if (originalUrl.includes("/appointments")) {
          // Try without trailing slash if it had one, or with trailing slash if it didn't
          const newUrl = originalUrl.endsWith("/") ? originalUrl.slice(0, -1) : originalUrl + "/";
          const originalParams = error.config?.params || {};
          return apiClient.get(newUrl, { params: originalParams });
        }
      }
      
      // Handle 401 Unauthorized - token expired or invalid
      if (status === 401) {
        // Check if token is expired
        const token = localStorage.getItem("access_token");
        if (token) {
          try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(
              atob(base64)
                .split('')
                .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join('')
            );
            const payload = JSON.parse(jsonPayload);
            const exp = payload.exp * 1000;
            const isExpired = Date.now() >= exp;
            
            if (isExpired) {
              // Token expired - try to refresh (if refresh endpoint exists)
              // For now, just redirect to login
              if (typeof window !== "undefined") {
                localStorage.removeItem("access_token");
                localStorage.removeItem("patient_id");
                window.location.href = "/login?expired=true";
              }
            } else {
              // Token invalid but not expired - clear and redirect
              if (typeof window !== "undefined") {
                localStorage.removeItem("access_token");
                localStorage.removeItem("patient_id");
                window.location.href = "/login?invalid=true";
              }
            }
          } catch {
            // Invalid token format - clear and redirect
            if (typeof window !== "undefined") {
              localStorage.removeItem("access_token");
              localStorage.removeItem("patient_id");
              window.location.href = "/login";
            }
          }
        } else {
          // No token - redirect to login
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
        }
      }
      
      // Handle 403 Forbidden
      if (status === 403) {
        throw new Error("You don't have permission to access this resource.");
      }
      
      // Handle 404 Not Found
      if (status === 404) {
        throw new Error("Resource not found.");
      }
      
      // Handle 429 Rate Limited
      if (status === 429) {
        throw new Error("Too many requests. Please try again in a minute.");
      }
      
      // Handle 502 Bad Gateway - upstream service unavailable
      if (status === 502) {
        const errorData = error.response.data as any;
        if (errorData?.message?.includes("upstream server")) {
          throw new Error("Service temporarily unavailable. The appointment service is starting up. Please wait a moment and try again.");
        }
        throw new Error("Service temporarily unavailable. Please try again in a moment.");
      }
      
      // Handle 503 Service Unavailable
      if (status === 503) {
        throw new Error("Service temporarily unavailable. Please try again in a moment.");
      }
      
      // Handle 500 Server Error
      if (status >= 500) {
        throw new Error("Server error. Please try again later.");
      }
      
      // Handle validation errors (400)
      if (status === 400 && error.response.data) {
        const data = error.response.data as { detail?: string; message?: string };
        throw new Error(data.detail || data.message || "Invalid request.");
      }
    } else if (error.request) {
      // Network error - provide more specific error message
      const url = error.config?.url || "API endpoint";
      const baseURL = error.config?.baseURL || "";
      const fullUrl = baseURL ? `${baseURL}${url}` : url;
      
      if (error.code === "ECONNREFUSED" || error.message?.includes("Network Error")) {
        throw new Error(`Cannot connect to API server at ${fullUrl}. Please ensure the backend services are running.`);
      } else if (error.code === "ERR_NETWORK") {
        throw new Error(`Network error: Unable to reach ${fullUrl}. Check your connection and ensure CORS is configured.`);
      } else {
        throw new Error(`Connection error: ${error.message || "Unable to connect to the server"}`);
      }
    } else {
      throw new Error(error.message || "An unexpected error occurred.");
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;

// Helper function to handle API errors
export function handleApiError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred.";
}
