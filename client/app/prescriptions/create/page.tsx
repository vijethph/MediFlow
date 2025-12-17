"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { FileUpload } from "@/components/ui/FileUpload";
import { useCreatePrescription } from "@/lib/hooks/usePrescriptions";
import { authApi } from "@/lib/api/auth";
import { prescriptionCreateSchema, type PrescriptionCreateFormData } from "@/lib/validations";
import { useNotificationContext } from "@/components/providers/NotificationProvider";
import { Plus, Trash2, Pill } from "lucide-react";

export default function CreatePrescriptionPage() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const createPrescription = useCreatePrescription();
  const { success, error: showError } = useNotificationContext();
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
    setError: setFormError,
  } = useForm<PrescriptionCreateFormData>({
    resolver: zodResolver(prescriptionCreateSchema),
    defaultValues: {
      medications: [{ medication_name: "", dosage: "", frequency: "", duration_days: 30 }],
      follow_up_required: false,
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "medications" });

  useEffect(() => {
    const authenticated = authApi.isAuthenticated();
    setIsAuthenticated(authenticated);
    setIsChecking(false);
    if (!authenticated) {
      router.replace("/login");
    }
  }, [router]);

  if (isChecking || !isAuthenticated) {
    return null;
  }

  const onSubmit = async (data: PrescriptionCreateFormData) => {
    try {
      const patientId = authApi.getPatientId();
      if (!patientId) {
        setFormError("root", { message: "Patient ID not found. Please log in again." });
        return;
      }

      await createPrescription.mutateAsync({ patient_id: patientId, ...data });

      success("Prescription Created", "Your prescription has been created successfully.");
      router.push("/prescriptions");
      router.refresh();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to create prescription. Please try again.";
      setFormError("root", { message: errorMessage });
      showError("Error", errorMessage);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Create New Prescription</h1>
        <p className="text-gray-600">Add a new prescription with medications and instructions</p>
      </div>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {errors.root && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{errors.root.message}</p>
            </div>
          )}

          <div>
            <Input
              label="Doctor Name"
              required
              {...register("doctor_name")}
              error={errors.doctor_name?.message}
              placeholder="Dr. Jane Smith"
            />
          </div>

          <div>
            <Input
              label="Diagnosis"
              required
              {...register("diagnosis")}
              error={errors.diagnosis?.message}
              placeholder="Primary diagnosis"
            />
          </div>

          <div>
            <label className="label">Medications</label>
            {fields.map((field, index) => (
              <Card key={field.id} className="mb-4 p-4 bg-gray-50">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-900">Medication {index + 1}</h3>
                  {fields.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => remove(index)}
                      className="text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Medication Name"
                    required
                    {...register(`medications.${index}.medication_name`)}
                    error={errors.medications?.[index]?.medication_name?.message}
                  />
                  <Input
                    label="Dosage"
                    required
                    {...register(`medications.${index}.dosage`)}
                    error={errors.medications?.[index]?.dosage?.message}
                    placeholder="e.g., 500mg"
                  />
                  <div>
                    <label className="label">
                      Frequency <span className="text-red-500">*</span>
                    </label>
                    <select
                      className={`input ${errors.medications?.[index]?.frequency ? "border-red-500" : ""}`}
                      {...register(`medications.${index}.frequency`)}
                    >
                      <option value="">Select frequency</option>
                      <option value="once_daily">Once Daily</option>
                      <option value="twice_daily">Twice Daily</option>
                      <option value="three_times_daily">Three Times Daily</option>
                      <option value="four_times_daily">Four Times Daily</option>
                      <option value="as_needed">As Needed</option>
                      <option value="every_morning">Every Morning</option>
                      <option value="every_evening">Every Evening</option>
                    </select>
                    {errors.medications?.[index]?.frequency && (
                      <p className="text-sm text-red-600 mt-1">
                        {errors.medications[index]?.frequency?.message}
                      </p>
                    )}
                  </div>
                  <Input
                    label="Duration (days)"
                    type="number"
                    required
                    {...register(`medications.${index}.duration_days`, { valueAsNumber: true })}
                    error={errors.medications?.[index]?.duration_days?.message}
                  />
                </div>
                <div className="mt-4">
                  <label className="label">Instructions (Optional)</label>
                  <textarea
                    className="input min-h-[80px]"
                    {...register(`medications.${index}.instructions`)}
                    placeholder="Special instructions for this medication"
                  />
                </div>
              </Card>
            ))}
            <Button
              type="button"
              variant="outline"
              onClick={() => append({ medication_name: "", dosage: "", frequency: "", duration_days: 30 })}
            >
              <Plus className="w-4 h-4" />
              Add Medication
            </Button>
            {errors.medications && (
              <p className="text-sm text-red-600 mt-2">{errors.medications.message}</p>
            )}
          </div>

          <div>
            <label className="label">Notes (Optional)</label>
            <textarea
              className="input min-h-[100px]"
              {...register("notes")}
              placeholder="Additional notes about the prescription"
            />
          </div>

          <div>
            <FileUpload
              label="Upload Prescription PDFs (Optional)"
              accept=".pdf,.jpg,.jpeg,.png"
              maxSize={10}
              multiple
              onFilesSelected={setUploadedFiles}
            />
          </div>

          <div className="flex gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.back()}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? (
                <>
                  <LoadingSpinner size="sm" />
                  Creating...
                </>
              ) : (
                <>
                  <Pill className="w-4 h-4" />
                  Create Prescription
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
