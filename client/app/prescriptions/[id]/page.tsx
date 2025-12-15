"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { usePrescription } from "@/lib/hooks/usePrescriptions";
import { authApi } from "@/lib/api/auth";
import { Pill, User, Calendar, ArrowLeft } from "lucide-react";

export default function PrescriptionDetailPage() {
  const router = useRouter();
  const params = useParams();
  const prescriptionId = params?.id as string;
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  const { data: prescription, isLoading, error } = usePrescription(prescriptionId || "");

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

  if (error || !prescription) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <ErrorMessage message={error?.message || "Prescription not found"} />
        <div className="mt-4">
          <Link href="/prescriptions">
            <Button variant="primary">Back to Prescriptions</Button>
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
      case "active":
        return "confirmed";
      case "pending":
        return "pending";
      case "expired":
        return "cancelled";
      case "filled":
        return "confirmed";
      default:
        return "pending";
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <Link href="/prescriptions">
        <Button variant="outline" className="mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Prescriptions
        </Button>
      </Link>

      <Card>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">Prescription Details</h1>
            <StatusBadge status={getStatusColor(prescription.status)}>
              {prescription.status === "active" ? "Active" :
               prescription.status === "pending" ? "Pending" :
               prescription.status === "expired" ? "Expired" :
               prescription.status === "filled" ? "Filled" :
               prescription.status}
            </StatusBadge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {(prescription.doctor_name || prescription.doctor_id) && (
              <div className="flex items-start gap-3">
                <User className="w-5 h-5 text-gray-400 mt-1" />
                <div>
                  <p className="text-sm text-gray-600">Prescribed By</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {prescription.doctor_name || prescription.doctor_id}
                  </p>
                </div>
              </div>
            )}

            {prescription.created_at && (
              <div className="flex items-start gap-3">
                <Calendar className="w-5 h-5 text-gray-400 mt-1" />
                <div>
                  <p className="text-sm text-gray-600">Prescribed On</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {formatDate(prescription.created_at)}
                  </p>
                </div>
              </div>
            )}
          </div>

          <div>
            <p className="text-sm text-gray-600 mb-2">Diagnosis</p>
            <p className="text-base font-semibold text-gray-900">{prescription.diagnosis}</p>
          </div>

          <div>
            <p className="text-sm text-gray-600 mb-3">Medications</p>
            <div className="space-y-4">
              {prescription.medications?.map((med, index) => (
                <Card key={index} className="p-4 bg-gray-50">
                  <div className="flex items-start gap-3 mb-2">
                    <Pill className="w-5 h-5 text-gray-400 mt-1" />
                    <div className="flex-1">
                      <p className="text-lg font-semibold text-gray-900">{med.medication_name}</p>
                      <p className="text-sm text-gray-600 mt-1">
                        <span className="font-medium">Dosage:</span> {med.dosage}
                      </p>
                      <p className="text-sm text-gray-600">
                        <span className="font-medium">Frequency:</span> {med.frequency}
                      </p>
                      <p className="text-sm text-gray-600">
                        <span className="font-medium">Duration:</span> {med.duration_days} days
                      </p>
                      {med.instructions && (
                        <p className="text-sm text-gray-600 mt-2">
                          <span className="font-medium">Instructions:</span> {med.instructions}
                        </p>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {prescription.notes && (
            <div>
              <p className="text-sm text-gray-600 mb-2">Notes</p>
              <p className="text-base text-gray-900">{prescription.notes}</p>
            </div>
          )}

          <div className="flex gap-4 pt-4 border-t border-gray-200">
            <Link href="/prescriptions">
              <Button variant="outline">Back</Button>
            </Link>
          </div>
        </div>
      </Card>
    </div>
  );
}
