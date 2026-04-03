'use client';

import { useMemo, useState, type FormEventHandler } from 'react';
import useSWR from 'swr';
import { Button } from '@/components/ui/button';
import { adapter } from '@/src/adapters';
import type { Transfer } from '@/src/adapters/types';
import { DataTable, StatusBadge } from '@/src/components/ui';
import { useAuth } from '@/src/context/auth-context';
import { usePINGate } from '@/src/context/pin-context';
import { useToast } from '@/src/context/toast-context';
import { formatDateTime, formatINR } from '@/src/lib/format';
import { DEMO_WHATSAPP_PHONE, WHATSAPP_TEMPLATES } from '@/src/lib/whatsapp-templates';

type TransferStep = 'details' | 'pin' | 'processing' | 'done';

function StepBadge({
  index,
  title,
  active,
  completed,
}: {
  index: number;
  title: string;
  active: boolean;
  completed: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
          completed ? 'bg-emerald-500 text-white' : active ? 'bg-[#00BAF2] text-white' : 'bg-slate-200 text-slate-600'
        }`}
      >
        {index}
      </span>
      <span className={`text-xs font-semibold ${active || completed ? 'text-[#002970]' : 'text-slate-500'}`}>{title}</span>
    </div>
  );
}

export default function MerchantTransfersPage() {
  const { session, pinVerified } = useAuth();
  const { requirePIN } = usePINGate();
  const toast = useToast();

  const [toUpiId, setToUpiId] = useState('');
  const [toName, setToName] = useState('');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [step, setStep] = useState<TransferStep>('details');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastTransfer, setLastTransfer] = useState<Transfer | null>(null);

  const { data, mutate } = useSWR(
    session?.merchantId ? (['merchant-transfer-page', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      const [wallet, audit] = await Promise.all([adapter.getWalletBalance(merchantId), adapter.getAuditLog(merchantId)]);
      return { wallet, audit };
    },
  );

  const transferHistory = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.audit
      .filter((row) => row.action.toLowerCase().includes('transfer'))
      .slice(0, 8)
      .map((row) => {
        const meta = row.metadata as Record<string, unknown>;
        return {
          date: row.timestamp,
          counterparty: String(meta.toName ?? meta.to_name ?? meta.toUpiId ?? meta.to_upi_id ?? meta.counterparty ?? '-'),
          amount: Number(row.amount ?? 0),
          status: row.outcome,
        };
      });
  }, [data]);

  const stepIndex =
    step === 'details' ? 1 : step === 'pin' ? 2 : step === 'processing' ? 3 : 4;

  const runTransfer = async () => {
    if (!session?.merchantId) {
      return;
    }

    const amountValue = Number(amount);
    if (!toUpiId.trim() || !toName.trim() || !Number.isFinite(amountValue) || amountValue <= 0) {
      toast.error('Enter valid transfer details.');
      return;
    }

    setIsSubmitting(true);
    setStep('processing');

    try {
      const result = await adapter.transfer({
        fromId: session.merchantId,
        toUpiId: toUpiId.trim(),
        toName: toName.trim(),
        amount: amountValue,
        note: note.trim(),
      });

      setLastTransfer(result);

      if (result.status !== 'success') {
        toast.error('Transfer failed. Please retry.');
        setStep('details');
        return;
      }

      const nextWallet = await adapter.getWalletBalance(session.merchantId);
      const message = WHATSAPP_TEMPLATES.transferSuccess({
        amount: result.amount,
        recipientName: result.toName,
        upiId: result.toUpiId,
        txId: result.txId,
        balance: nextWallet.balance,
      });
      await adapter.sendWhatsappAlert({
        merchantId: session.merchantId,
        phone: DEMO_WHATSAPP_PHONE,
        message,
      });

      toast.success(`Transferred ${formatINR(result.amount)} to ${result.toName}.`);
      toast.whatsapp('Transfer confirmation sent on WhatsApp.', DEMO_WHATSAPP_PHONE);

      setAmount('');
      setNote('');
      await mutate();
      setStep('done');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Transfer failed.');
      setStep('details');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit: FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();

    if (pinVerified) {
      void runTransfer();
      return;
    }

    setStep('pin');
    requirePIN({
      message: 'Enter your UPI PIN to authorize this transfer.',
      actionLabel: 'Authorize Transfer',
      onSuccess: () => {
        void runTransfer();
      },
    });
  };

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Transfer Money</p>
        <h1 className="mt-1 text-2xl font-black text-[#002970]">Wallet to Bank or UPI</h1>
        <p className="mt-1 text-sm text-slate-600">
          Available balance: <span className="font-bold text-[#002970]">{data ? formatINR(data.wallet.balance) : 'Loading...'}</span>
        </p>

        <div className="mt-4 flex flex-wrap gap-4">
          <StepBadge index={1} title="Details" active={stepIndex === 1} completed={stepIndex > 1} />
          <StepBadge index={2} title="PIN" active={stepIndex === 2} completed={stepIndex > 2} />
          <StepBadge index={3} title="Processing" active={stepIndex === 3} completed={stepIndex > 3} />
          <StepBadge index={4} title="Done" active={stepIndex === 4} completed={stepIndex > 4} />
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="paytm-surface p-5">
          <h2 className="text-lg font-black text-[#002970]">Transfer Form</h2>
          <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
            <label className="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              Recipient UPI ID
              <input
                value={toUpiId}
                onChange={(event) => setToUpiId(event.target.value)}
                placeholder="supplier@icici"
                className="mt-1 h-11 w-full rounded-xl border border-[#d1daea] px-3 text-sm text-slate-700 outline-none focus:border-[#00BAF2]"
                required
              />
            </label>

            <label className="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              Recipient Name
              <input
                value={toName}
                onChange={(event) => setToName(event.target.value)}
                placeholder="ABC Suppliers"
                className="mt-1 h-11 w-full rounded-xl border border-[#d1daea] px-3 text-sm text-slate-700 outline-none focus:border-[#00BAF2]"
                required
              />
            </label>

            <label className="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              Amount
              <input
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="25000"
                type="number"
                min={1}
                className="mt-1 h-11 w-full rounded-xl border border-[#d1daea] px-3 text-sm text-slate-700 outline-none focus:border-[#00BAF2]"
                required
              />
            </label>

            <label className="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              Note (optional)
              <input
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Raw material settlement"
                className="mt-1 h-11 w-full rounded-xl border border-[#d1daea] px-3 text-sm text-slate-700 outline-none focus:border-[#00BAF2]"
              />
            </label>

            <Button
              type="submit"
              disabled={isSubmitting}
              className="mt-1 h-11 w-full rounded-full bg-[#002970] text-white hover:bg-[#0a3f9d]"
            >
              {isSubmitting ? 'Processing transfer...' : 'Transfer Money'}
            </Button>
          </form>

          {lastTransfer ? (
            <div className="mt-4 rounded-2xl border border-[#d5def0] bg-[#f8fbff] p-3 text-sm text-slate-700">
              <p className="font-semibold text-[#002970]">Last transfer: {lastTransfer.txId}</p>
              <p className="mt-1">Recipient: {lastTransfer.toName}</p>
              <p className="mt-1">Amount: {formatINR(lastTransfer.amount)}</p>
              <p className="mt-1">Time: {formatDateTime(lastTransfer.timestamp)}</p>
            </div>
          ) : null}
        </article>

        <article className="paytm-surface p-5">
          <h2 className="text-lg font-black text-[#002970]">Recent Transfers</h2>
          <div className="mt-3">
            <DataTable
              columns={[
                { key: 'date', header: 'Date', render: (value) => formatDateTime(String(value)) },
                { key: 'counterparty', header: 'Counterparty' },
                {
                  key: 'amount',
                  header: 'Amount',
                  render: (value) => <span className="font-semibold text-[#002970]">{formatINR(Number(value))}</span>,
                },
                {
                  key: 'status',
                  header: 'Status',
                  render: (value) => <StatusBadge status={String(value) === 'success' ? 'PAID' : 'OVERDUE'} />,
                },
              ]}
              data={transferHistory as unknown as Record<string, unknown>[]}
            />
          </div>
        </article>
      </section>
    </div>
  );
}
