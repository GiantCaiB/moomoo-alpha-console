"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import Shell from "@/components/layout/Shell";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchInterval: 15000,
            staleTime: 5000,
            retry: 1,
          },
        },
      })
  );

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-accent-green font-mono text-lg animate-pulse">
          Initializing...
        </div>
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Shell>{children}</Shell>
    </QueryClientProvider>
  );
}
