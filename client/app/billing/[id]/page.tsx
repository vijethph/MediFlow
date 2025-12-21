"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useInvoice, useCreatePayment } from "@/lib/hooks/useBilling";
import { authApi } from "@/lib/api/auth";
import { Receipt, Calendar, DollarSign, ArrowLeft } from "lucide-react";
import { useNotificationContext } from "@/components/providers/NotificationProvider";

export default function InvoiceDetailPage() {
  const router = useRouter();
  const params = useParams();
  const invoiceId = params?.id as string;
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const createPayment = useCreatePayment();
  const { success, error: showError } = useNotificationContext();

  const { data: invoice, isLoading, error } = useInvoice(invoiceId || "");

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

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <ErrorMessage message={error?.message || "Invoice not found"} />
        <div className="mt-4">
          <Link href="/billing">
            <Button variant="primary">Back to Billing</Button>
          </Link>
        </div>
      </div>
    );
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "balanced":
        return "confirmed";
      case "issued":
        return "pending";
      case "cancelled":
        return "cancelled";
      default:
        return "pending";
    }
  };

  // Helper function to extract numeric value from Decimal/Money object
  const extractValue = (val: any): number => {
    if (val === null || val === undefined) return 0;
    if (typeof val === "number") return val;
    if (typeof val === "string") return parseFloat(val) || 0;
    if (typeof val === "object" && val !== null && val.value !== undefined) {
      return typeof val.value === "number"
        ? val.value
        : parseFloat(String(val.value)) || 0;
    }
    return 0;
  };

  const totalAmount = extractValue(
    invoice.total || invoice.total_gross_amount || invoice.totalGross
  );

  const handlePayNow = async () => {
    if (confirm(`Pay €${totalAmount.toFixed(2)} for this invoice?`)) {
      try {
        await createPayment.mutateAsync({
          invoice_id: invoice.id,
          amount: totalAmount,
          payment_method: "card",
        });
        success(
          "Payment Processed",
          "Your payment has been processed successfully."
        );
        router.refresh();
      } catch (err: any) {
        showError(
          "Payment Failed",
          err.message || "Payment could not be processed. Please try again."
        );
      }
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <Link href="/billing">
        <Button variant="outline" className="mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Billing
        </Button>
      </Link>

      <Card>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Invoice #{invoice.id.slice(0, 8)}
              </h1>
              <p className="text-sm text-gray-600 mt-1">Invoice Details</p>
            </div>
            <StatusBadge status={getStatusColor(invoice.status)}>
              {invoice.status === "balanced"
                ? "Paid"
                : invoice.status === "issued"
                ? "Awaiting Payment"
                : invoice.status === "cancelled"
                ? "Cancelled"
                : invoice.status}
            </StatusBadge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex items-start gap-3">
              <Calendar className="w-5 h-5 text-gray-400 mt-1" />
              <div>
                <p className="text-sm text-gray-600">Issue Date</p>
                <p className="text-lg font-semibold text-gray-900">
                  {formatDate(invoice.issue_date || invoice.date || "")}
                </p>
              </div>
            </div>

            {invoice.due_date && (
              <div className="flex items-start gap-3">
                <Calendar className="w-5 h-5 text-gray-400 mt-1" />
                <div>
                  <p className="text-sm text-gray-600">Due Date</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {formatDate(invoice.due_date)}
                  </p>
                </div>
              </div>
            )}
          </div>

          {invoice.description && (
            <div>
              <p className="text-sm text-gray-600 mb-2">Description</p>
              <p className="text-base text-gray-900">{invoice.description}</p>
            </div>
          )}

          {invoice.line_items && invoice.line_items.length > 0 && (
            <div>
              <p className="text-sm text-gray-600 mb-3">Line Items</p>
              <div className="space-y-2">
                {invoice.line_items.map((item, index) => {
                  const unitPrice = extractValue(item.unit_price);
                  const lineTotal = extractValue(item.line_total);
                  return (
                    <div
                      key={index}
                      className="flex justify-between items-center p-3 bg-gray-50 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-gray-900">
                          {item.description || "Item"}
                        </p>
                        <p className="text-sm text-gray-600">
                          {item.quantity} × €{unitPrice.toFixed(2)}
                        </p>
                      </div>
                      <p className="font-semibold text-gray-900">
                        €{lineTotal.toFixed(2)}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <DollarSign className="w-6 h-6 text-blue-600" />
                <div>
                  <p className="text-sm text-gray-600">Total Amount</p>
                  <p className="text-3xl font-bold text-blue-900">
                    €{totalAmount.toFixed(2)}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {invoice.status === "issued" && (
            <div className="flex gap-4 pt-4 border-t border-gray-200">
              <Button
                variant="primary"
                onClick={handlePayNow}
                disabled={createPayment.isPending}
              >
                {createPayment.isPending ? "Processing..." : "Pay Now"}
              </Button>
            </div>
          )}

          <div className="flex gap-4 pt-4 border-t border-gray-200">
            <Link href="/billing">
              <Button variant="outline">Back</Button>
            </Link>
          </div>
        </div>
      </Card>
    </div>
  );
}
