"use client";

import { QueryProvider } from "./QueryProvider";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { NotificationProvider } from "./NotificationProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <NotificationProvider>
        <AuthLayout>{children}</AuthLayout>
      </NotificationProvider>
    </QueryProvider>
  );
}

