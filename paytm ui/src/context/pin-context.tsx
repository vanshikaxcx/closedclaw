'use client';

import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { PINModal } from '@/src/components/ui/PINModal';

interface PINRequest {
  message?: string;
  actionLabel?: string;
  onSuccess: () => void;
}

interface PINContextValue {
  requirePIN: (request: PINRequest) => void;
}

const PINContext = createContext<PINContextValue | undefined>(undefined);

export function PINProvider({ children }: { children: React.ReactNode }) {
  const [request, setRequest] = useState<PINRequest | null>(null);

  const requirePIN = useCallback((nextRequest: PINRequest) => {
    setRequest(nextRequest);
  }, []);

  const handleSuccess = useCallback(() => {
    if (request) {
      request.onSuccess();
    }
    setRequest(null);
  }, [request]);

  const handleCancel = useCallback(() => {
    setRequest(null);
  }, []);

  const value = useMemo<PINContextValue>(() => ({ requirePIN }), [requirePIN]);

  return (
    <PINContext.Provider value={value}>
      {children}
      <PINModal
        open={!!request}
        onSuccess={handleSuccess}
        onCancel={handleCancel}
        message={request?.message}
        actionLabel={request?.actionLabel}
      />
    </PINContext.Provider>
  );
}

export function usePINGate(): PINContextValue {
  const context = useContext(PINContext);
  if (!context) {
    throw new Error('usePINGate must be used inside PINProvider');
  }
  return context;
}
