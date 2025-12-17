import { HTMLAttributes } from "react";
import { clsx } from "clsx";

interface StatusBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  status: string;
}

export function StatusBadge({ status, className, ...props }: StatusBadgeProps) {
  const getStatusClass = (status: string) => {
    const lowerStatus = status.toLowerCase();
    if (lowerStatus.includes("confirmed") || lowerStatus.includes("paid") || lowerStatus.includes("filled") || lowerStatus === "active") {
      return "badge-success";
    }
    if (lowerStatus.includes("pending") || lowerStatus.includes("warning")) {
      return "badge-warning";
    }
    if (lowerStatus.includes("cancelled") || lowerStatus.includes("failed") || lowerStatus === "expired") {
      return "badge-danger";
    }
    return "badge-info";
  };

  return (
    <span className={clsx("badge", getStatusClass(status), className)} {...props}>
      {status}
    </span>
  );
}
