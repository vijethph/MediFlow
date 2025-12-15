"use client";

import { useState, useCallback } from "react";
import { Notification, NotificationType } from "@/components/ui/Notification";

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback(
    (
      type: NotificationType,
      title: string,
      message?: string,
      duration: number = 5000
    ) => {
      const id = `${Date.now()}-${Math.random()}`;
      const notification: Notification = {
        id,
        type,
        title,
        message,
        duration,
      };

      setNotifications((prev) => [...prev, notification]);
      return id;
    },
    []
  );

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const success = useCallback(
    (title: string, message?: string, duration?: number) => {
      return addNotification("success", title, message, duration);
    },
    [addNotification]
  );

  const error = useCallback(
    (title: string, message?: string, duration?: number) => {
      return addNotification("error", title, message, duration);
    },
    [addNotification]
  );

  const info = useCallback(
    (title: string, message?: string, duration?: number) => {
      return addNotification("info", title, message, duration);
    },
    [addNotification]
  );

  const warning = useCallback(
    (title: string, message?: string, duration?: number) => {
      return addNotification("warning", title, message, duration);
    },
    [addNotification]
  );

  return {
    notifications,
    addNotification,
    removeNotification,
    success,
    error,
    info,
    warning,
  };
}
