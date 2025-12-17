import { z } from "zod";

// Medication schema
const medicationSchema = z.object({
  medication_name: z.string().min(1, "Medication name is required"),
  dosage: z.string().min(1, "Dosage is required"),
  frequency: z.string().min(1, "Frequency is required"),
  duration_days: z.number().min(1, "Duration must be at least 1 day").max(365, "Duration cannot exceed 365 days"),
  instructions: z.string().optional(),
  quantity: z.number().min(1, "Quantity must be at least 1").optional(),
});

// Prescription creation validation schema
export const prescriptionCreateSchema = z.object({
  doctor_name: z.string().min(1, "Doctor name is required"),
  doctor_id: z.string().optional(),
  appointment_id: z.string().optional(),
  medications: z.array(medicationSchema).min(1, "At least one medication is required"),
  diagnosis: z.string().min(1, "Diagnosis is required"),
  notes: z.string().optional(),
  lab_tests_ordered: z.array(z.string()).optional(),
  follow_up_required: z.boolean().optional(),
  follow_up_days: z.number().min(1).max(365).optional(),
});

export type PrescriptionCreateFormData = z.infer<typeof prescriptionCreateSchema>;
