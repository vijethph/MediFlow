"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useCreateInvoice } from "@/lib/hooks/useBilling";
import { authApi } from "@/lib/api/auth";
import {
  invoiceCreateSchema,
  type InvoiceCreateFormData,
} from "@/lib/validations";
import { useNotificationContext } from "@/components/providers/NotificationProvider";
import { Plus, Trash2, DollarSign } from "lucide-react";

export default function CreateInvoicePage() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const createInvoice = useCreateInvoice();
  const { success, error: showError } = useNotificationContext();
  const [calculatedTotal, setCalculatedTotal] = useState(0);

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors, isSubmitting },
    setError: setFormError,
    setValue,
  } = useForm<InvoiceCreateFormData>({
    resolver: zodResolver(invoiceCreateSchema),
    defaultValues: {
      line_items: [{ description: "", quantity: 1, unit_price: 0 }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "line_items",
  });
  const lineItems = watch("line_items");

  useEffect(() => {
    const authenticated = authApi.isAuthenticated();
    setIsAuthenticated(authenticated);
    setIsChecking(false);
    if (!authenticated) {
      router.replace("/login");
    }
  }, [router]);

  useEffect(() => {
    if (lineItems && lineItems.length > 0) {
      const total = lineItems.reduce((sum, item) => {
        const quantity = Number(item.quantity) || 0;
        const unitPrice = Number(item.unit_price) || 0;
        return sum + quantity * unitPrice;
      }, 0);
      setCalculatedTotal(total);
      setValue("total", total, { shouldValidate: true });
    } else {
      setCalculatedTotal(0);
      setValue("total", 0, { shouldValidate: true });
    }
  }, [JSON.stringify(lineItems), setValue]);

  if (isChecking || !isAuthenticated) {
    return null;
  }

  const onSubmit = async (data: InvoiceCreateFormData) => {
    try {
      const patientId = authApi.getPatientId();
      if (!patientId) {
        setFormError("root", {
          message: "Patient ID not found. Please log in again.",
        });
        return;
      }

      await createInvoice.mutateAsync({
        ...data,
        subject: patientId,
      });

      success(
        "Invoice Created",
        "Your invoice has been generated successfully."
      );
      router.push("/billing");
      router.refresh();
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : "Failed to create invoice. Please try again.";
      setFormError("root", { message: errorMessage });
      showError("Error", errorMessage);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Generate New Invoice
        </h1>
        <p className="text-gray-600">Create a new invoice with line items</p>
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
              label="Due Date"
              type="date"
              required
              {...register("due_date")}
              error={errors.due_date?.message}
            />
          </div>

          <div>
            <label className="label">Line Items</label>
            {fields.map((field, index) => (
              <Card key={field.id} className="mb-4 p-4 bg-gray-50">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-900">
                    Item {index + 1}
                  </h3>
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
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Input
                    label="Description"
                    required
                    {...register(`line_items.${index}.description`)}
                    error={errors.line_items?.[index]?.description?.message}
                    placeholder="Service description"
                  />
                  <Input
                    label="Quantity"
                    type="number"
                    required
                    {...register(`line_items.${index}.quantity`, {
                      valueAsNumber: true,
                    })}
                    error={errors.line_items?.[index]?.quantity?.message}
                  />
                  <Input
                    label="Unit Price (€)"
                    type="number"
                    step="0.01"
                    required
                    {...register(`line_items.${index}.unit_price`, {
                      valueAsNumber: true,
                    })}
                    error={errors.line_items?.[index]?.unit_price?.message}
                  />
                </div>
                {lineItems?.[index] && (
                  <p className="text-sm text-gray-600 mt-2">
                    Subtotal: €
                    {(
                      (lineItems[index].quantity || 0) *
                      (lineItems[index].unit_price || 0)
                    ).toFixed(2)}
                  </p>
                )}
              </Card>
            ))}
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                append({ description: "", quantity: 1, unit_price: 0 })
              }
            >
              <Plus className="w-4 h-4" />
              Add Line Item
            </Button>
          </div>

          <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-900">Total Amount:</span>
              <span className="text-2xl font-bold text-blue-900">
                €{calculatedTotal.toFixed(2)}
              </span>
            </div>
          </div>

          <div>
            <label className="label">Description (Optional)</label>
            <textarea
              className="input min-h-[100px]"
              {...register("description")}
              placeholder="Additional notes about the invoice"
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
                  Generating...
                </>
              ) : (
                <>
                  <DollarSign className="w-4 h-4" />
                  Generate Invoice
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
