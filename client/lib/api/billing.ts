import apiClient from "./client";

export interface Invoice {
  id: string;
  resource_type?: string;
  subject: string; // patient_id
  status: "draft" | "issued" | "balanced" | "cancelled" | "entered-in-error";
  date: string; // Invoice date
  total?: {
    value: number;
    currency: string;
  };
  totalGross?: {
    value: number;
    currency: string;
  };
  totalNet?: {
    value: number;
    currency: string;
  };
  line_items?: Array<{
    id: string;
    sequence: number;
    code: string;
    description?: string;
    quantity: number;
    unit_price: {
      value: number;
      currency: string;
    };
    line_total: {
      value: number;
      currency: string;
    };
  }>;
  payment_terms?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
  // Computed fields for UI
  amount_due?: number; // Computed from total
  issue_date?: string; // Alias for date
  due_date?: string; // Computed from date + payment_terms
  description?: string; // Computed from line_items or notes
}

export interface InvoiceList {
  total: number;
  count: number;
  skip: number;
  limit: number;
  items: Invoice[];
}

export interface Payment {
  id: string;
  invoice_id: string;
  amount: number;
  status: "pending" | "completed" | "failed" | "refunded";
  payment_method?: string;
  transaction_id?: string;
  created_at?: string;
}

export interface PaymentCreate {
  invoice_id: string;
  amount: {
    value: number;
    currency: string;
  };
  payment_method: string;
  payment_date?: string;
  transaction_id?: string;
  notes?: string;
}

export const billingApi = {
  getInvoice: async (invoiceId: string): Promise<Invoice> => {
    const response = await apiClient.get<Invoice>(`/api/v1/invoices/${invoiceId}`);
    return response.data;
  },

  listInvoices: async (params?: {
    subject?: string; // patient_id
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<InvoiceList> => {
    // Backend requires patient_id as query parameter
    if (!params?.subject) {
      throw new Error("patient_id is required");
    }
    const response = await apiClient.get<any>("/api/v1/invoices", {
      params: {
        patient_id: params.subject,
        skip: params.skip || 0,
        limit: params.limit || 100,
      },
    });
    // Transform response
    const data = response.data;
    const invoices = (data.items || []).map((inv: any) => {
      const totalGross = inv.total_gross_amount || inv.totalGross || 0;
      const totalDue = inv.total_due_amount || inv.totalDue || 0;
      const date = inv.date ? new Date(inv.date) : new Date();
      const dueDate = inv.payment_terms 
        ? new Date(date.getTime() + 30 * 24 * 60 * 60 * 1000) // Default 30 days
        : date;
      
      return {
        ...inv,
        id: inv.id || inv.invoice_id,
        total: typeof totalGross === "object" ? totalGross.value : totalGross,
        amount_due: typeof totalDue === "object" ? totalDue.value : totalDue,
        issue_date: date.toISOString().split("T")[0],
        due_date: dueDate.toISOString().split("T")[0],
        description: inv.line_items?.[0]?.description || inv.notes || "Invoice",
      };
    });
    
    return {
      total: data.total || invoices.length,
      count: invoices.length,
      skip: params.skip || 0,
      limit: params.limit || 100,
      items: invoices,
    };
  },

  createInvoice: async (data: {
    subject: string;
    total: number;
    due_date: string;
    description?: string;
    line_items?: Array<{
      description: string;
      quantity: number;
      unit_price: number;
    }>;
  }): Promise<Invoice> => {
    // Transform frontend format to backend format
    // Backend expects: subject (patient_id), date (datetime), line_items with Money type
    const backendData = {
      subject: data.subject,
      date: new Date().toISOString(), // Use current date for invoice date
      line_items: (data.line_items || []).map((item, index) => ({
        sequence: index + 1,
        code: `ITEM-${index + 1}`, // Generate code if not provided
        description: item.description || "",
        quantity: item.quantity,
        unit_price: {
          value: item.unit_price,
          currency: "EUR", // Use EUR as per user's request
        },
        line_total: {
          value: item.quantity * item.unit_price,
          currency: "EUR",
        },
      })),
      payment_terms: `Net 30`, // Default payment terms
      notes: data.description || "",
    };
    
    const response = await apiClient.post<Invoice>("/api/v1/invoices", backendData);
    const responseData = response.data;
    
    // Transform backend response to frontend format
    const responseDataAny = responseData as any; // Type assertion for backend response
    return {
      ...responseData,
      id: responseData.id || "",
      subject: responseData.subject || data.subject,
      date: responseData.date || new Date().toISOString(),
      total: typeof responseDataAny.total_gross_amount === "object" 
        ? responseDataAny.total_gross_amount.value 
        : responseDataAny.total_gross_amount || data.total,
      amount_due: typeof responseDataAny.total_due_amount === "object"
        ? responseDataAny.total_due_amount.value
        : responseDataAny.total_due_amount || data.total,
      issue_date: responseData.date ? new Date(responseData.date).toISOString().split("T")[0] : "",
      due_date: data.due_date,
      description: responseDataAny.notes || data.description || "",
      line_items: responseData.line_items || [],
    };
  },

  createPayment: async (data: PaymentCreate): Promise<Payment> => {
    // Transform to backend format
    // Backend expects PaymentRecordCreate with amount: Money, payment_date: datetime
    const paymentData = {
      invoice_id: data.invoice_id,
      amount: typeof data.amount === "number" 
        ? { value: data.amount, currency: "EUR" } // Use EUR as per user's request
        : { ...data.amount, currency: data.amount.currency || "EUR" },
      payment_method: data.payment_method,
      payment_date: data.payment_date || new Date().toISOString(),
      reference_number: data.transaction_id, // Backend uses reference_number
      notes: data.notes,
    };
    const response = await apiClient.post<any>("/api/v1/payments", paymentData);
    const payment = response.data;
    return {
      id: payment.id || payment.payment_id || "",
      invoice_id: payment.invoice_id || data.invoice_id,
      amount: typeof payment.amount === "object" ? payment.amount.value : payment.amount,
      status: payment.payment_status || payment.status || "pending",
      payment_method: payment.payment_method || data.payment_method,
      transaction_id: payment.reference_number || payment.transaction_id || data.transaction_id,
      created_at: payment.created_at || payment.payment_date || new Date().toISOString(),
    };
  },

  getPayment: async (paymentId: string): Promise<Payment> => {
    const response = await apiClient.get<Payment>(`/api/v1/payments/${paymentId}`);
    return response.data;
  },
};
