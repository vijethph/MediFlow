import { z } from "zod";

// Appointment booking validation schema
export const appointmentBookingSchema = z.object({
  practitioner_name: z.string().min(1, "Practitioner name is required"),
  practitioner_id: z.string().optional(),
  start: z.string().min(1, "Start date and time is required"),
  duration: z.enum(["30", "60"], {
    message: "Duration must be either 30 or 60 minutes",
  }),
  description: z.string().optional(),
  location: z.string().optional(),
  service_type: z.string().optional(),
  specialty: z.string().optional(),
  appointment_type: z.string().optional(),
  comment: z.string().optional(),
}).refine((data) => {
  const start = new Date(data.start);
  const now = new Date();
  return start > now;
}, {
  message: "Start time must be in the future",
  path: ["start"],
});

export type AppointmentBookingFormData = z.infer<typeof appointmentBookingSchema>;
