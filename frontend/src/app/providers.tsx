"use client";

import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { useState, useEffect, createContext, useContext } from "react";
import { api } from "@/lib/api";
import type { BrokerHealthResponse } from "@/lib/types";
import Shell from "@/components/layout/Shell";

interface BrokerHealthContextValue {
  health: BrokerHealthResponse | null;
  isLoading: boolean;
}

const BrokerHealthContext = createContext<BrokerHealthContextValue>({
  health: null,
  isLoading: true,
});

export const useBrokerHealth = () => useContext(BrokerHealthContext);

function BrokerHealthProvider({ children }: { children: React.ReactNode }) {
  const { data, isLoading } = useQuery({
    queryKey: ["brokerHealth"],
    queryFn: api.brokerHealth,
    refetchInterval: 10000,
  });

  return (
    <BrokerHealthContext.Provider value={{ health: data ?? null, isLoading }}>
      {children}
    </BrokerHealthContext.Provider>
  );
}

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
      <BrokerHealthProvider>
        <Shell>{children}</Shell>
      </BrokerHealthProvider>
    </QueryClientProvider>
  );
}
