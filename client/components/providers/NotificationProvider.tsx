"use client";

import { createContext, useContext, ReactNode } from "react";
import { NotificationContainer } from "@/components/ui/Notification";
import { useNotifications } from "@/lib/hooks/useNotifications";
import type { NotificationType } from "@/components/ui/Notification";

interface NotificationContextType {
  notifications: ReturnType<typeof useNotifications>["notifications"];
  addNotification: (type: NotificationType, title: string, message?: string, duration?: number) => void;
  removeNotification: (id: string) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const notifications = useNotifications();

  const success = (title: string, message?: string) => {
    notifications.addNotification("success", title, message, 5000);
  };

  const error = (title: string, message?: string) => {
    notifications.addNotification("error", title, message, 7000);
  };

  const info = (title: string, message?: string) => {
    notifications.addNotification("info", title, message, 5000);
  };

  const warning = (title: string, message?: string) => {
    notifications.addNotification("warning", title, message, 6000);
  };

  return (
    <NotificationContext.Provider
      value={{
        notifications: notifications.notifications,
        addNotification: notifications.addNotification,
        removeNotification: notifications.removeNotification,
        success,
        error,
        info,
        warning,
      }}
    >
      {children}
      <NotificationContainer
        notifications={notifications.notifications}
        onDismiss={notifications.removeNotification}
      />
    </NotificationContext.Provider>
  );
}

export function useNotificationContext() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error("useNotificationContext must be used within a NotificationProvider");
  }
  return context;
}
