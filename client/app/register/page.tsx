"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { authApi, RegisterData } from "@/lib/api/auth";
import { registerSchema, type RegisterFormData } from "@/lib/validations";

export default function RegisterPage() {
  const router = useRouter();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError: setFormError,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    try {
      // Build FHIR-compatible registration data
      const nameParts = {
        use: "official" as const,
        family: data.lastName || undefined,
        given: data.firstName ? [data.firstName] : undefined,
        text: `${data.firstName} ${data.lastName}`.trim() || undefined,
      };

      const telecom: Array<{ system: string; value: string; use?: string }> = [
        { system: "email", value: data.email, use: "home" },
      ];
      
      if (data.phone) {
        telecom.push({ system: "phone", value: data.phone, use: "home" });
      }

      const registerData: RegisterData = {
        name: [nameParts],
        telecom,
        email: data.email,
        password: data.password, // Password will be hashed by backend
        ...(data.birthDate && { birth_date: data.birthDate }),
        ...(data.gender && { gender: data.gender }),
      };

      await authApi.register(registerData);
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      setFormError("root", {
        message: err instanceof Error ? err.message : "Registration failed. Please try again.",
      });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100 px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo and Branding */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
            <span className="text-white text-2xl font-bold">H</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Create Your Account
          </h1>
          <p className="text-base text-gray-600 mb-3">
            Register to access your healthcare portal
          </p>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 border border-blue-200 rounded-full">
            <span className="text-xs font-semibold text-blue-900">FHIR R4</span>
            <span className="text-xs text-blue-700">Compatible</span>
          </div>
        </div>

        <Card className="shadow-xl">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {errors.root && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{errors.root.message}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="First Name"
              required
              {...register("firstName")}
              error={errors.firstName?.message}
              disabled={isSubmitting}
            />
            <Input
              label="Last Name"
              required
              {...register("lastName")}
              error={errors.lastName?.message}
              disabled={isSubmitting}
            />
          </div>

          <Input
            label="Email"
            type="email"
            required
            {...register("email")}
            placeholder="your.email@example.com"
            error={errors.email?.message}
            disabled={isSubmitting}
          />

          <Input
            label="Password"
            type="password"
            required
            {...register("password")}
            placeholder="Create a strong password"
            error={errors.password?.message}
            disabled={isSubmitting}
            autoComplete="new-password"
          />

          <Input
            label="Confirm Password"
            type="password"
            required
            {...register("confirmPassword")}
            placeholder="Confirm your password"
            error={errors.confirmPassword?.message}
            disabled={isSubmitting}
            autoComplete="new-password"
          />

          <Input
            label="Phone (Optional)"
            type="tel"
            {...register("phone")}
            placeholder="(555) 123-4567"
            error={errors.phone?.message}
            disabled={isSubmitting}
          />

          <Input
            label="Date of Birth (Optional)"
            type="date"
            {...register("birthDate")}
            error={errors.birthDate?.message}
            disabled={isSubmitting}
          />

          <div className="mb-4">
            <label htmlFor="gender" className="label">
              Gender (Optional)
            </label>
            <select
              id="gender"
              className="input"
              {...register("gender")}
              disabled={isSubmitting}
            >
              <option value="">Select gender</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
            {errors.gender && (
              <p className="text-sm text-red-600 mt-1">{errors.gender.message}</p>
            )}
          </div>

          <Button
            type="submit"
            variant="primary"
            className="w-full"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <LoadingSpinner size="sm" />
                Creating account...
              </>
            ) : (
              "Register"
            )}
          </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-center text-sm text-gray-600">
              Already have an account?{" "}
              <a 
                href="/login" 
                className="text-blue-600 hover:underline font-medium transition-colors"
              >
                Sign in here
              </a>
            </p>
          </div>
        </Card>

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-xs text-gray-500">
            Secure healthcare management system
          </p>
        </div>
      </div>
    </div>
  );
}
