import { HTMLAttributes } from "react";
import { clsx } from "clsx";

interface LoadingSpinnerProps extends HTMLAttributes<HTMLDivElement> {
  size?: "sm" | "md" | "lg";
}

export function LoadingSpinner({ size = "md", className, ...props }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
  };

  return (
    <div
      className={clsx("spinner", sizeClasses[size], className)}
      {...props}
      aria-label="Loading"
    />
  );
}
