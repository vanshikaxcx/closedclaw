'use client';

import React from 'react';
import { Button } from '@/components/ui/button';

interface ArthsetuErrorBoundaryProps {
  children: React.ReactNode;
}

interface ArthsetuErrorBoundaryState {
  hasError: boolean;
}

export class ArthsetuErrorBoundary extends React.Component<ArthsetuErrorBoundaryProps, ArthsetuErrorBoundaryState> {
  constructor(props: ArthsetuErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ArthsetuErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown): void {
    console.error('ArthSetu boundary caught an error', error);
  }

  private reset = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="paytm-surface p-5">
          <p className="text-base font-bold text-[#002970]">ArthSetu encountered an issue</p>
          <p className="mt-1 text-sm text-slate-600">Please retry this section. Your session is still active.</p>
          <Button className="mt-3 rounded-full bg-[#002970] hover:bg-[#0a3f9d]" onClick={this.reset}>
            Retry
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
