import { HTMLAttributes } from "react";
import { AlertCircle } from "lucide-react";
import { clsx } from "clsx";

interface ErrorMessageProps extends HTMLAttributes<HTMLDivElement> {
  message: string;
}

export function ErrorMessage({ message, className, ...props }: ErrorMessageProps) {
  return (
    <div
      className={clsx(
        "flex items-center gap-2 p-3 rounded-md bg-red-50 text-red-800 border border-red-200",
        className
      )}
      role="alert"
      {...props}
    >
      <AlertCircle className="w-5 h-5 flex-shrink-0" />
      <span className="text-sm font-medium">{message}</span>
    </div>
  );
}
