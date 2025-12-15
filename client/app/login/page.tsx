"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { authApi } from "@/lib/api/auth";
import { loginSchema, type LoginFormData } from "@/lib/validations";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [expiredMessage, setExpiredMessage] = useState<string | null>(null);
  
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError: setFormError,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  useEffect(() => {
    const expired = searchParams.get("expired");
    const invalid = searchParams.get("invalid");
    if (expired === "true") {
      setExpiredMessage("Your session has expired. Please log in again.");
    } else if (invalid === "true") {
      setExpiredMessage("Invalid authentication token. Please log in again.");
    }
  }, [searchParams]);

  const onSubmit = async (data: LoginFormData) => {
    try {
      await authApi.login({ email: data.email, password: data.password });
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      setFormError("root", {
        message: err instanceof Error ? err.message : "Login failed. Please check your credentials and try again.",
      });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
            <span className="text-white text-3xl font-bold">H</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Healthcare Portal
          </h1>
          <p className="text-base text-gray-600 mb-3">
            Sign in to access your medical records
          </p>
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 border border-blue-200 rounded-full">
            <span className="text-xs font-semibold text-blue-900">FHIR R4</span>
            <span className="text-xs text-blue-700">Compatible</span>
          </div>
        </div>

        <Card className="shadow-xl">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {expiredMessage && (
              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                <p className="text-sm text-yellow-800">{expiredMessage}</p>
              </div>
            )}
            {errors.root && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-800">{errors.root.message}</p>
              </div>
            )}

            <div>
              <Input
                label="Email Address"
                type="email"
                required
                {...register("email")}
                placeholder="your.email@example.com"
                disabled={isSubmitting}
                autoFocus
                autoComplete="email"
                error={errors.email?.message}
              />
            </div>

            <div>
              <Input
                label="Password"
                type="password"
                required
                {...register("password")}
                placeholder="Enter your password"
                disabled={isSubmitting}
                autoComplete="current-password"
                error={errors.password?.message}
              />
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
                  Signing in...
                </>
              ) : (
                "Sign In"
              )}
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-center text-sm text-gray-600">
              Don't have an account?{" "}
              <a href="/register" className="text-blue-600 hover:underline font-medium">
                Register here
              </a>
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
