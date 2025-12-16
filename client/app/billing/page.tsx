"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Receipt, DollarSign, Search, Plus, FileText } from "lucide-react";
import { useInvoices, useCreatePayment } from "@/lib/hooks/useBilling";
import { authApi } from "@/lib/api/auth";
import { useNotificationContext } from "@/components/providers/NotificationProvider";

export default function BillingPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  
  useEffect(() => {
    if (!authApi.isAuthenticated()) {
      router.replace("/login");
      return;
    }
  }, [router]);
  
  if (!authApi.isAuthenticated()) {
    return null;
  }
  
  const { data, isLoading, error: invoiceError } = useInvoices();
  const createPayment = useCreatePayment();
  const { success, error: showError } = useNotificationContext();

  const invoices = data?.items || [];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "paid":
        return "paid";
      case "issued":
        return "awaiting";
      case "overdue":
        return "failed";
      case "cancelled":
        return "cancelled";
      default:
        return "awaiting";
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const filteredInvoices = invoices.filter((inv) => {
    // Status filtering
    if (statusFilter && inv.status !== statusFilter) {
      return false;
    }
    
    // Search filtering
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesSearch = 
        inv.id.toLowerCase().includes(query) ||
        inv.description?.toLowerCase().includes(query);
      if (!matchesSearch) return false;
    }
    
    return true;
  });

  // Calculate pagination on filtered results
  const totalPages = Math.ceil(filteredInvoices.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;

  // Apply pagination
  const paginatedInvoices = filteredInvoices.slice(startIndex, endIndex);

  const handlePayNow = async (invoiceId: string, amount: number) => {
    if (confirm(`Pay €${amount.toFixed(2)} for this invoice?`)) {
      try {
        await createPayment.mutateAsync({
          invoice_id: invoiceId,
          amount,
          payment_method: "card",
        });
        success("Payment Processed", "Your payment has been processed successfully.");
        router.refresh();
      } catch (err: any) {
        showError("Payment Failed", err.message || "Payment could not be processed. Please try again.");
      }
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (invoiceError) {
    const errorMessage = invoiceError instanceof Error ? invoiceError.message : "Failed to load invoices. Please try again.";
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-8">
        <ErrorMessage message={errorMessage} />
        <div className="mt-4">
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    );
  }

  const outstandingBalance = invoices
    .filter((inv) => inv.status === "issued" || inv.status === "balanced")
    .reduce((sum, inv) => sum + (inv.amount_due || 0), 0);

  const recentCharges = invoices
    .filter((inv) => {
      const invDate = new Date(inv.issue_date || inv.date || "");
      const thisMonth = new Date();
      thisMonth.setDate(1);
      return invDate >= thisMonth;
    })
    .reduce((sum, inv) => sum + (typeof inv.total === "number" ? inv.total : inv.total?.value || 0), 0);

  const nextPaymentDue = invoices
    .filter((inv) => inv.status === "issued" || inv.status === "balanced")
    .sort((a, b) => new Date(a.due_date || a.date || "").getTime() - new Date(b.due_date || b.date || "").getTime())[0];

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Billing & Payments</h1>
          <p className="text-base text-gray-600">Handle billing and payments</p>
        </div>
        <Link href="/billing/invoice/create">
          <Button variant="primary" className="mt-4 sm:mt-0 bg-orange-600 hover:bg-orange-700">
            <Plus className="w-4 h-4" aria-hidden="true" />
            Generate Invoice
          </Button>
        </Link>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Card>
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Outstanding Balance</p>
            <DollarSign className="w-5 h-5 text-danger" aria-hidden="true" />
          </div>
          <p className="text-3xl font-bold text-gray-900">
            €{outstandingBalance.toFixed(2)}
          </p>
        </Card>
        <Card>
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Recent Charges</p>
            <Receipt className="w-5 h-5 text-gray-600" aria-hidden="true" />
          </div>
          <p className="text-3xl font-bold text-gray-900">
            €{recentCharges.toFixed(2)}
          </p>
        </Card>
        <Card>
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-600">Next Payment Due</p>
            <FileText className="w-5 h-5 text-warning" aria-hidden="true" />
          </div>
          {nextPaymentDue ? (
            <>
              <p className="text-base text-gray-900 mb-1">{formatDate(nextPaymentDue.due_date || nextPaymentDue.date || "")}</p>
              <p className="text-sm text-gray-600">€{(nextPaymentDue.amount_due || 0).toFixed(2)}</p>
            </>
          ) : (
            <p className="text-base text-gray-500">No pending payments</p>
          )}
        </Card>
      </div>

      {/* Search Bar */}
      <Card className="mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search 
              className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" 
              aria-hidden="true" 
            />
            <input
              type="text"
              placeholder="Search invoices by patient, invoice number..."
              className="input pl-10 w-full"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search invoices"
            />
          </div>
          <select
            className="input md:w-48 w-full md:w-auto"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
          >
            <option value="">All Status</option>
            <option value="balanced">Paid</option>
            <option value="issued">Pending</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </Card>

      {/* Invoices Table */}
      <Card>
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900">Invoices</h2>
        </div>
        {filteredInvoices.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse" role="table">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Description</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredInvoices.map((invoice) => (
                  <tr key={invoice.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(invoice.issue_date || invoice.date || "")}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {invoice.description || invoice.notes || "Invoice"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                      €{(typeof invoice.total === "number" ? invoice.total : invoice.total?.value || 0).toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={getStatusColor(invoice.status)}>
                        {invoice.status === "balanced" ? "Paid" :
                         invoice.status === "issued" ? "Awaiting Payment" :
                         invoice.status === "cancelled" ? "Cancelled" :
                         invoice.status}
                      </StatusBadge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex gap-2">
                        <Link href={`/billing/${invoice.id}`}>
                          <Button variant="ghost" className="text-xs">View</Button>
                        </Link>
                        {(invoice.status === "issued" || invoice.status === "balanced") && (invoice.amount_due || 0) > 0 && (
                          <Button
                            variant="primary"
                            onClick={() => handlePayNow(invoice.id, invoice.amount_due || 0)}
                            disabled={createPayment.isPending}
                            className="text-xs"
                          >
                            {createPayment.isPending ? "Processing..." : "Pay Now"}
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <Receipt className="w-12 h-12 text-gray-400 mx-auto mb-4" aria-hidden="true" />
            <p className="text-base text-gray-600">No invoices found.</p>
          </div>
        )}
      </Card>
    </div>
  );
}
