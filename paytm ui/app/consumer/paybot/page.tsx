'use client';

import { useEffect, useMemo, useState } from 'react';
import { Bot, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { formatINR } from '@/src/lib/format';

interface Message {
  id: string;
  role: 'user' | 'bot';
  text: string;
}

export default function ConsumerPaybotPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'seed',
      role: 'bot',
      text: 'Hi! I am PayBot. Tell me what you need and I will plan your purchase.',
    },
  ]);
  const [input, setInput] = useState('Need groceries for this week under 500');
  const [typing, setTyping] = useState(false);
  const [showIntentCard, setShowIntentCard] = useState(false);
  const [showAgentSteps, setShowAgentSteps] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);
  const [showHitl, setShowHitl] = useState(false);
  const [hitlCounter, setHitlCounter] = useState(30);
  const [approved, setApproved] = useState(false);

  const intentAmount = 213;

  useEffect(() => {
    if (!showHitl || approved) {
      return;
    }

    const timer = window.setInterval(() => {
      setHitlCounter((current) => {
        if (current <= 1) {
          window.clearInterval(timer);
          return 0;
        }
        return current - 1;
      });
    }, 1000);

    return () => window.clearInterval(timer);
  }, [approved, showHitl]);

  const submitMessage = () => {
    if (!input.trim()) {
      return;
    }

    const userMessage: Message = {
      id: `u_${Date.now()}`,
      role: 'user',
      text: input.trim(),
    };

    setMessages((current) => [...current, userMessage]);
    setInput('');
    setTyping(true);

    window.setTimeout(() => {
      setTyping(false);
      setMessages((current) => [
        ...current,
        {
          id: `b_${Date.now()}`,
          role: 'bot',
          text: 'I parsed your request. Please review this intent card.',
        },
      ]);
      setShowIntentCard(true);
    }, 1500);
  };

  const startAgentFlow = () => {
    setShowAgentSteps(true);

    const feed = [
      'Searching merchants...',
      'Found Ramesh General Store',
      'Building order basket...',
      `Total computed: ${formatINR(intentAmount)}`,
      'HITL approval required (amount exceeds Rs. 200 threshold).',
    ];

    feed.forEach((entry, index) => {
      window.setTimeout(() => {
        setSteps((current) => [...current, entry]);
        if (index === feed.length - 1) {
          setShowHitl(true);
        }
      }, index * 1000);
    });
  };

  const receipt = useMemo(
    () => ({
      orderId: 'PB-2026-0412',
      merchant: 'Ramesh General Store',
      total: intentAmount,
    }),
    [],
  );

  return (
    <div className="paytm-surface relative min-h-[78vh] overflow-hidden p-4 pb-24">
      <div className="mb-3 flex items-center gap-2 text-[#002970]">
        <Bot size={18} />
        <h1 className="text-xl font-black">PayBot</h1>
      </div>

      <div className="space-y-3 pb-32">
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
                message.role === 'user' ? 'bg-[#002970] text-white' : 'border border-[#d8e0ef] bg-white text-slate-700'
              }`}
            >
              {message.text}
            </div>
          </div>
        ))}

        {typing ? (
          <div className="inline-flex items-center gap-1 rounded-xl border border-[#d8e0ef] bg-white px-3 py-2 text-slate-500">
            <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.2s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.1s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" />
          </div>
        ) : null}

        {showIntentCard ? (
          <div className="rounded-2xl border border-[#d8e2f4] bg-[#f4f8ff] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#00BAF2]">Intent Card</p>
            <div className="mt-2 grid gap-1 text-sm text-slate-700">
              <p>Items: Grocery staples</p>
              <p>Budget cap: {formatINR(500)}</p>
              <p>Categories: Grocery</p>
              <p>Time validity: 15 minutes</p>
            </div>
            <Button onClick={startAgentFlow} className="mt-3 rounded-full bg-[#002970] hover:bg-[#0a3f9d]">
              Looks right?
            </Button>
          </div>
        ) : null}

        {showAgentSteps ? (
          <div className="rounded-2xl border border-[#d8e2f4] bg-white p-4">
            <p className="text-sm font-semibold text-[#002970]">Agent Steps</p>
            <div className="mt-2 space-y-1 text-xs text-slate-600">
              {steps.map((entry, index) => (
                <p key={`${entry}-${index}`}>- {entry}</p>
              ))}
            </div>
          </div>
        ) : null}

        {showHitl && !approved ? (
          <div className="rounded-2xl border border-[#F59E0B]/40 bg-[#FFF7E8] p-4">
            <p className="text-sm font-semibold text-[#8a5a02]">Human-in-the-loop approval required</p>
            <p className="mt-1 text-sm text-[#8a5a02]">
              Send {formatINR(intentAmount)} to Ramesh General Store? Countdown: {hitlCounter}s
            </p>
            <div className="mt-3 flex gap-2">
              <Button
                onClick={() => setApproved(true)}
                className="rounded-full bg-[#002970] hover:bg-[#0a3f9d]"
              >
                Approve
              </Button>
              <Button variant="outline" className="rounded-full border-red-400 text-red-600 hover:bg-red-50">
                Cancel
              </Button>
            </div>
          </div>
        ) : null}

        {approved ? (
          <div className="rounded-2xl border border-[#d8e2f4] bg-[#f4f8ff] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#00BAF2]">Receipt</p>
            <p className="mt-2 text-sm text-slate-700">Order ID: {receipt.orderId}</p>
            <p className="text-sm text-slate-700">Merchant: {receipt.merchant}</p>
            <p className="text-sm font-semibold text-[#002970]">Total: {formatINR(receipt.total)}</p>
          </div>
        ) : null}
      </div>

      <div className="absolute inset-x-4 bottom-4 flex items-center gap-2 rounded-2xl border border-[#d8e2f4] bg-white p-2">
        <Input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Tell me what you need..."
          className="h-10 border-none"
        />
        <Button onClick={submitMessage} className="h-10 rounded-full bg-[#002970] px-4 hover:bg-[#0a3f9d]">
          <Send size={14} />
        </Button>
      </div>
    </div>
  );
}
