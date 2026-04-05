'use client';

import { MessageCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ArthsetuErrorBoundary } from '@/src/components/shared/ArthsetuErrorBoundary';

function TaxAssistantContent() {
  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#00BAF2]">GST VoiceBot</p>
        <h2 className="mt-2 text-xl font-black text-[#002970]">Tax Assistant</h2>
        <p className="mt-2 text-sm text-slate-600">
          Ask GST questions through voice or text. Use the floating VoiceBot at the bottom-right on any merchant page.
        </p>

        <Button
          className="mt-4 rounded-full bg-[#002970] hover:bg-[#0a3f9d]"
          onClick={() => {
            window.dispatchEvent(new Event('arthsetu:open-voicebot'));
          }}
        >
          <MessageCircle size={16} />
          Open VoiceBot
        </Button>
      </section>

      <section className="paytm-surface p-5">
        <h3 className="text-base font-black text-[#002970]">How It Works</h3>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">
          <li>Voice mode records your question and sends it to GST voice processing.</li>
          <li>Text mode is the fallback for denied microphone access.</li>
          <li>Conversation stays in-memory for the current session only.</li>
        </ul>
      </section>
    </div>
  );
}

export default function TaxAssistantPage() {
  return (
    <ArthsetuErrorBoundary>
      <TaxAssistantContent />
    </ArthsetuErrorBoundary>
  );
}
