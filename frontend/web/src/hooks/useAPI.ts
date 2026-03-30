import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../services/api';

export function useMarkets(params?: Record<string, any>) {
  return useQuery({
    queryKey: ['markets', params],
    queryFn: () => api.fetchMarkets(params),
  });
}

export function useTrades(params?: Record<string, any>) {
  return useQuery({
    queryKey: ['trades', params],
    queryFn: () => api.fetchTrades(params),
  });
}

export function usePositions(params?: Record<string, any>) {
  return useQuery({
    queryKey: ['positions', params],
    queryFn: () => api.fetchPositions(params),
  });
}

export function useWallets() {
  return useQuery({
    queryKey: ['wallets'],
    queryFn: api.fetchWallets,
  });
}

export function usePerformance(days: number = 7) {
  return useQuery({
    queryKey: ['performance', days],
    queryFn: () => api.fetchPerformance(days),
  });
}

export function useAIImpact(days: number = 30) {
  return useQuery({
    queryKey: ['ai-impact', days],
    queryFn: () => api.fetchAIImpact(days),
  });
}

export function useAlerts(params?: Record<string, any>) {
  return useQuery({
    queryKey: ['alerts', params],
    queryFn: () => api.fetchAlerts(params),
  });
}

export function useTradeStats() {
  return useQuery({
    queryKey: ['trade-stats'],
    queryFn: api.fetchTradeStats,
  });
}

export function useOptimize() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (days: number) => api.runOptimization(days),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ai'] }),
  });
}

export function usePostTradeAnalysis() {
  return useMutation({
    mutationFn: (days: number) => api.runPostTradeAnalysis(days),
  });
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => api.acknowledgeAlert(alertId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }),
  });
}
