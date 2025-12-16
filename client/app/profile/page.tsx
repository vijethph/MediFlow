"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Modal } from "@/components/ui/Modal";
import { User, Shield, Bell, FileText } from "lucide-react";
import { usePatient, useUpdatePatient } from "@/lib/hooks/usePatient";
import { authApi } from "@/lib/api/auth";
import { useNotificationContext } from "@/components/providers/NotificationProvider";
import { profileUpdateSchema, changePasswordSchema, type ProfileUpdateFormData, type ChangePasswordFormData } from "@/lib/validations/profile";

export default function ProfilePage() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showAllergiesModal, setShowAllergiesModal] = useState(false);
  const [activeSection, setActiveSection] = useState("profile");
  const [notificationPrefs, setNotificationPrefs] = useState({
    appointmentReminders: true,
    prescriptionRefills: true,
    billingNotifications: true,
  });
  
  // Always call hooks at the top - never conditionally
  const { data: patient, isLoading, error } = usePatient();
  const updatePatient = useUpdatePatient();
  const { success, error: showError } = useNotificationContext();
  
  // Profile form
  const profileForm = useForm<ProfileUpdateFormData>({
    resolver: zodResolver(profileUpdateSchema),
  });
  
  // Password form
  const passwordForm = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
  });
  
  
  useEffect(() => {
    const authenticated = authApi.isAuthenticated();
    setIsAuthenticated(authenticated);
    setIsChecking(false);
    
    if (!authenticated) {
      router.replace("/login");
      return;
    }
  }, [router]);
  
  // Populate profile form when patient data loads
  useEffect(() => {
    if (patient && !isEditing) {
      const name = patient.name?.[0];
      profileForm.reset({
        firstName: name?.given?.join(" ") || "",
        lastName: name?.family || "",
        email: patient.email || "",
        phone: patient.phone || "",
        birthDate: patient.birth_date || "",
        address: "", // Address not available in current Patient interface
      });
    }
  }, [patient, isEditing, profileForm]);
  
  // Handle scroll to section
  useEffect(() => {
    if (activeSection) {
      const element = document.getElementById(activeSection);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }, [activeSection]);
  
  // Early return AFTER all hooks
  if (isChecking || !isAuthenticated) {
    return null;
  }

  const handleProfileSubmit = async (data: ProfileUpdateFormData) => {
    try {
      const patientId = authApi.getPatientId();
      if (!patientId) {
        showError("Error", "Patient ID not found. Please log in again.");
        return;
      }
      
      await updatePatient.mutateAsync({
        full_name: `${data.firstName} ${data.lastName}`.trim(),
        email: data.email,
        phone: data.phone || undefined,
        date_of_birth: data.birthDate || undefined,
        address: data.address || undefined,
      });
      
      setIsEditing(false);
      success("Profile Updated", "Your profile has been updated successfully.");
      router.refresh();
    } catch (err: any) {
      showError("Update Failed", err.message || "Failed to update profile. Please try again.");
    }
  };
  
  const handlePasswordSubmit = async (data: ChangePasswordFormData) => {
    try {
      await authApi.changePassword({
        currentPassword: data.currentPassword,
        newPassword: data.newPassword,
      });
      setShowPasswordModal(false);
      passwordForm.reset();
      success("Password Changed", "Your password has been changed successfully. Please log in again.");
      // Logout and redirect to login after password change
      setTimeout(() => {
        authApi.logout();
        router.push("/login");
      }, 2000);
    } catch (err: any) {
      // If endpoint doesn't exist (404), show helpful message
      if (err.message?.includes("404") || err.message?.includes("Not Found")) {
        showError("Not Available", "Password change endpoint is not yet implemented in the backend. This feature will be available soon.");
      } else {
        showError("Password Change Failed", err.message || "Failed to change password. Please try again.");
      }
    }
  };
  
  
  const handleNotificationToggle = async (key: keyof typeof notificationPrefs) => {
    const newValue = !notificationPrefs[key];
    setNotificationPrefs({ ...notificationPrefs, [key]: newValue });
    // TODO: Save notification preferences to backend when endpoint is available
    success("Preferences Updated", "Your notification preferences have been saved.");
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

  if (error) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-8">
        <ErrorMessage message="Failed to load profile. Please try again." />
      </div>
    );
  }

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Settings</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Settings Navigation */}
        <div className="lg:col-span-1">
          <Card>
            <nav aria-label="Settings navigation">
              <ul className="space-y-1" role="list">
                <li>
                  <button
                    onClick={() => setActiveSection("profile")}
                    className={`w-full flex items-center gap-3 px-3 py-3 rounded-sm text-sm font-medium ${
                      activeSection === "profile"
                        ? "text-primary bg-primary-light border-l-[3px] border-primary"
                        : "text-gray-700 hover:bg-gray-100"
                    }`}
                  >
                    <User className="w-5 h-5" aria-hidden="true" />
                    Personal Information
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setActiveSection("medical-history")}
                    className={`w-full flex items-center gap-3 px-3 py-3 rounded-sm text-sm font-medium ${
                      activeSection === "medical-history"
                        ? "text-primary bg-primary-light border-l-[3px] border-primary"
                        : "text-gray-700 hover:bg-gray-100"
                    }`}
                  >
                    <FileText className="w-5 h-5" aria-hidden="true" />
                    Medical History
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setActiveSection("notifications")}
                    className={`w-full flex items-center gap-3 px-3 py-3 rounded-sm text-sm font-medium ${
                      activeSection === "notifications"
                        ? "text-primary bg-primary-light border-l-[3px] border-primary"
                        : "text-gray-700 hover:bg-gray-100"
                    }`}
                  >
                    <Bell className="w-5 h-5" aria-hidden="true" />
                    Notification Preferences
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => setActiveSection("security")}
                    className={`w-full flex items-center gap-3 px-3 py-3 rounded-sm text-sm font-medium ${
                      activeSection === "security"
                        ? "text-primary bg-primary-light border-l-[3px] border-primary"
                        : "text-gray-700 hover:bg-gray-100"
                    }`}
                  >
                    <Shield className="w-5 h-5" aria-hidden="true" />
                    Security Settings
                  </button>
                </li>
              </ul>
            </nav>
          </Card>
        </div>

        {/* Settings Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Profile Tab */}
          <Card id="profile">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-semibold text-gray-900">Personal Information</h2>
              {!isEditing && (
                <Button variant="secondary" onClick={() => setIsEditing(true)}>
                  Edit
                </Button>
              )}
            </div>
            {isEditing ? (
              <form onSubmit={profileForm.handleSubmit(handleProfileSubmit)}>
                {profileForm.formState.errors.root && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm text-red-800">{profileForm.formState.errors.root.message}</p>
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="First Name"
                    required
                    {...profileForm.register("firstName")}
                    error={profileForm.formState.errors.firstName?.message}
                  />
                  <Input
                    label="Last Name"
                    required
                    {...profileForm.register("lastName")}
                    error={profileForm.formState.errors.lastName?.message}
                  />
                </div>
                <Input
                  label="Date of Birth"
                  type="date"
                  {...profileForm.register("birthDate")}
                  error={profileForm.formState.errors.birthDate?.message}
                  hint="Format: YYYY-MM-DD"
                />
                <Input
                  label="Email"
                  type="email"
                  required
                  {...profileForm.register("email")}
                  error={profileForm.formState.errors.email?.message}
                />
                <Input
                  label="Phone"
                  type="tel"
                  {...profileForm.register("phone")}
                  error={profileForm.formState.errors.phone?.message}
                  hint="Format: (555) 123-4567"
                />
                <Input
                  label="Address"
                  {...profileForm.register("address")}
                  error={profileForm.formState.errors.address?.message}
                />
                <div className="mt-6 flex gap-2">
                  <Button
                    type="submit"
                    variant="primary"
                    disabled={updatePatient.isPending}
                  >
                    {updatePatient.isPending ? (
                      <>
                        <LoadingSpinner size="sm" />
                        Saving...
                      </>
                    ) : (
                      "Save Changes"
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setIsEditing(false);
                      profileForm.reset();
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            ) : (
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600">Name</p>
                  <p className="text-base text-gray-900">
                    {patient?.name?.[0]?.given?.join(" ")} {patient?.name?.[0]?.family}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Email</p>
                  <p className="text-base text-gray-900">
                    {patient?.email || "N/A"}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Phone</p>
                  <p className="text-base text-gray-900">
                    {patient?.phone || "N/A"}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Date of Birth</p>
                  <p className="text-base text-gray-900">
                    {patient?.birth_date || "N/A"}
                  </p>
                </div>
              </div>
            )}
          </Card>

          {/* Medical History Tab */}
          <Card id="medical-history">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Medical History</h2>
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-danger mb-2">Allergies</h3>
              <div className="bg-red-50 border border-red-200 rounded-sm p-3">
                <p className="text-base text-gray-700">
                  {patient?.allergies || "No known allergies"}
                </p>
              </div>
              <p className="text-sm text-gray-500 mt-2">
                Note: Allergy updates require backend support. Contact your healthcare provider to update this information.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Current Medications</h3>
              <div className="bg-gray-50 border border-gray-200 rounded-sm p-3">
                <p className="text-base text-gray-700">
                  {patient?.current_medications || "None recorded"}
                </p>
              </div>
            </div>
          </Card>

          {/* Notification Preferences Tab */}
          <Card id="notifications">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Notification Preferences</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-base font-medium text-gray-700">
                    Appointment reminders (24 hours before)
                  </p>
                  <p className="text-sm text-gray-500">Email</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={notificationPrefs.appointmentReminders}
                    onChange={() => handleNotificationToggle("appointmentReminders")}
                  />
                  <div className={`w-11 h-6 rounded-full transition-colors duration-200 ${
                    notificationPrefs.appointmentReminders ? "bg-blue-600" : "bg-gray-200"
                  } peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all ${
                    notificationPrefs.appointmentReminders ? "after:translate-x-full" : ""
                  }`}></div>
                </label>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-base font-medium text-gray-700">
                    Prescription refill updates
                  </p>
                  <p className="text-sm text-gray-500">Email</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={notificationPrefs.prescriptionRefills}
                    onChange={() => handleNotificationToggle("prescriptionRefills")}
                  />
                  <div className={`w-11 h-6 rounded-full transition-colors duration-200 ${
                    notificationPrefs.prescriptionRefills ? "bg-blue-600" : "bg-gray-200"
                  } peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all ${
                    notificationPrefs.prescriptionRefills ? "after:translate-x-full" : ""
                  }`}></div>
                </label>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-base font-medium text-gray-700">
                    Billing notifications
                  </p>
                  <p className="text-sm text-gray-500">Email</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={notificationPrefs.billingNotifications}
                    onChange={() => handleNotificationToggle("billingNotifications")}
                  />
                  <div className={`w-11 h-6 rounded-full transition-colors duration-200 ${
                    notificationPrefs.billingNotifications ? "bg-blue-600" : "bg-gray-200"
                  } peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all ${
                    notificationPrefs.billingNotifications ? "after:translate-x-full" : ""
                  }`}></div>
                </label>
              </div>
            </div>
          </Card>

          {/* Security Settings Tab */}
          <Card id="security">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Security Settings</h2>
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Change Password</h3>
                <p className="text-base text-gray-600 mb-4">
                  Update your password to keep your account secure.
                </p>
                <Button variant="secondary" onClick={() => {
                  passwordForm.reset();
                  setShowPasswordModal(true);
                }}>
                  Change Password
                </Button>
              </div>
              <div className="pt-4 border-t border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Active Sessions</h3>
                <p className="text-base text-gray-600 mb-2">
                  Manage devices where you're signed in.
                </p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <div>
                      <p className="text-sm font-medium text-gray-900">Current Session</p>
                      <p className="text-xs text-gray-500">Active now</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
      
      {/* Change Password Modal */}
      <Modal
        isOpen={showPasswordModal}
        onClose={() => {
          setShowPasswordModal(false);
          passwordForm.reset();
        }}
        title="Change Password"
        size="md"
      >
        <form onSubmit={passwordForm.handleSubmit(handlePasswordSubmit)} className="space-y-4">
          {passwordForm.formState.errors.root && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{passwordForm.formState.errors.root.message}</p>
            </div>
          )}
          
          <Input
            label="Current Password"
            type="password"
            required
            {...passwordForm.register("currentPassword")}
            error={passwordForm.formState.errors.currentPassword?.message}
            autoComplete="current-password"
          />
          
          <Input
            label="New Password"
            type="password"
            required
            {...passwordForm.register("newPassword")}
            error={passwordForm.formState.errors.newPassword?.message}
            autoComplete="new-password"
            hint="Must be at least 8 characters with uppercase, lowercase, number, and special character"
          />
          
          <Input
            label="Confirm New Password"
            type="password"
            required
            {...passwordForm.register("confirmPassword")}
            error={passwordForm.formState.errors.confirmPassword?.message}
            autoComplete="new-password"
          />
          
          <div className="flex gap-2 pt-4">
            <Button
              type="submit"
              variant="primary"
              className="flex-1"
              disabled={passwordForm.formState.isSubmitting}
            >
              {passwordForm.formState.isSubmitting ? (
                <>
                  <LoadingSpinner size="sm" />
                  Changing...
                </>
              ) : (
                "Change Password"
              )}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setShowPasswordModal(false);
                passwordForm.reset();
              }}
            >
              Cancel
            </Button>
          </div>
        </form>
      </Modal>
      
    </div>
  );
}
