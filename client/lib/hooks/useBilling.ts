import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { billingApi, Invoice, PaymentCreate } from "@/lib/api/billing";
import { authApi } from "@/lib/api/auth";
import { handleApiError } from "@/lib/api/client";

export function useInvoices(filters?: { status?: string }) {
  const [patientId, setPatientId] = useState<string | null>(null);
  
  useEffect(() => {
    setPatientId(authApi.getPatientId());
  }, []);
  
  return useQuery({
    queryKey: ["invoices", filters, patientId],
    queryFn: () => {
      if (!patientId) {
        throw new Error("Patient ID is required");
      }
      return billingApi.listInvoices({
        subject: patientId,
        ...filters,
      });
    },
    enabled: !!patientId,
  });
}

export function useInvoice(invoiceId: string) {
  return useQuery({
    queryKey: ["invoice", invoiceId],
    queryFn: () => billingApi.getInvoice(invoiceId),
    enabled: !!invoiceId,
  });
}

export function useCreateInvoice() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: { subject: string; total: number; due_date: string; description?: string; line_items?: Array<{ description: string; quantity: number; unit_price: number }> }) => 
      billingApi.createInvoice(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (error) => {
      throw handleApiError(error);
    },
  });
}

export function useCreatePayment() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: { invoice_id: string; amount: number; payment_method: string }) => 
      billingApi.createPayment({
        invoice_id: data.invoice_id,
        amount: { value: data.amount, currency: "EUR" },
        payment_method: data.payment_method,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (error) => {
      throw handleApiError(error);
    },
  });
}
