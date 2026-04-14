import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000,       // 2 min
      gcTime:    10 * 60 * 1000,       // 10 min cache
      refetchOnWindowFocus: false,
      retry: (failureCount, error: any) => {
        // Don't retry 404s
        if (error?.message?.includes('404')) return false;
        return failureCount < 2;
      },
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
    },
    mutations: {
      retry: 0,
    },
  },
});
