"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, createContext, useContext } from "react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
    },
  },
});

// ─── Toast context ────────────────────────────────────────────────────────────
type Toast = { id: string; message: string; type: "success" | "error" | "info" };
type ToastCtx = { addToast: (msg: string, type?: Toast["type"]) => void };

export const ToastContext = createContext<ToastCtx>({ addToast: () => {} });
export const useToast = () => useContext(ToastContext);

export default function Providers({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = (message: string, type: Toast["type"] = "info") => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  };

  const toastColors = {
    success: "var(--accent-emerald)",
    error: "var(--accent-rose)",
    info: "var(--accent-blue)",
  };

  return (
    <QueryClientProvider client={queryClient}>
      <ToastContext.Provider value={{ addToast }}>
        {children}

        {/* Toast container */}
        <div className="toast">
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className="toast-item animate-fade-in"
              style={{ borderLeft: `3px solid ${toastColors[toast.type]}` }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: toastColors[toast.type],
                  flexShrink: 0,
                }}
              />
              <span style={{ color: "var(--text-primary)" }}>{toast.message}</span>
            </div>
          ))}
        </div>
      </ToastContext.Provider>
    </QueryClientProvider>
  );
}
