"use client";

import { usePathname } from "next/navigation";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { authApi } from "@/lib/api/auth";

export function AuthLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname === "/login" || pathname === "/register";

  // For auth pages, show minimal layout
  if (isAuthPage) {
    return (
      <>
        <a href="#main-content" className="skip-link sr-only">
          Skip to main content
        </a>
        <main id="main-content" className="min-h-screen">
          {children}
        </main>
      </>
    );
  }

  // For protected pages, show full layout with header and sidebar
  return (
    <>
      <a href="#main-content" className="skip-link sr-only">
        Skip to main content
      </a>
      <Header />
      <div className="flex pt-16">
        <Sidebar />
        <main id="main-content" className="flex-1 md:ml-64 min-h-screen p-6">
          {children}
        </main>
      </div>
    </>
  );
}
