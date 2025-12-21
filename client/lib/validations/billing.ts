import { z } from "zod";

// Invoice generation validation schema
export const invoiceCreateSchema = z.object({
  total: z.number().min(0.01, "Total must be greater than 0"),
  due_date: z.string().min(1, "Due date is required"),
  description: z.string().optional(),
  line_items: z
    .array(
      z.object({
        description: z.string().min(1, "Item description is required"),
        quantity: z.number().min(1, "Quantity must be at least 1"),
        unit_price: z.number().min(0.01, "Unit price must be greater than 0"),
      })
    )
    .min(1, "At least one line item is required"),
});

export type InvoiceCreateFormData = z.infer<typeof invoiceCreateSchema>;

// Payment validation schema
export const paymentSchema = z.object({
  invoice_id: z.string().min(1, "Invoice ID is required"),
  amount: z.number().min(0.01, "Amount must be greater than 0"),
  payment_method: z.string().min(1, "Payment method is required"),
});

export type PaymentFormData = z.infer<typeof paymentSchema>;
