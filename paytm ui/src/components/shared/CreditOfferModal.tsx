'use client';

import { Button } from '@/components/ui/button';
import type { CreditOffer, Invoice } from '@/src/adapters/types';
import { Modal } from '@/src/components/ui/Modal';
import { usePINGate } from '@/src/context/pin-context';
import { formatINR } from '@/src/lib/format';

interface CreditOfferModalProps {
  open: boolean;
  offer: CreditOffer | null;
  invoice: Invoice | null;
  onClose: () => void;
  onAccept: () => Promise<void>;
  onDecline: () => Promise<void>;
}

export function CreditOfferModal({ open, offer, invoice, onClose, onAccept, onDecline }: CreditOfferModalProps) {
  const { requirePIN } = usePINGate();

  if (!offer || !invoice) {
    return null;
  }

  const feeAmount = Math.round((offer.advanceAmount * offer.feeRate) / 100);
  const repayAmount = offer.advanceAmount + feeAmount;
  const effectiveApr = (offer.feeRate * 12).toFixed(1);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Credit Offer Summary"
      footer={
        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={() => {
              void onDecline();
            }}
          >
            Decline
          </Button>
          <Button
            className="bg-[#002970] hover:bg-[#0a3f9d]"
            onClick={() => {
              requirePIN({
                message: `Confirm: Accept ${formatINR(offer.advanceAmount)} advance at ${offer.feeRate}% fee.`,
                actionLabel: 'Accept Offer',
                onSuccess: () => {
                  void onAccept();
                },
              });
            }}
          >
            Accept Offer
          </Button>
        </div>
      }
    >
      <div className="space-y-3 text-sm text-slate-700">
        <div className="rounded-xl border border-[#E5E7EB] bg-[#f8fbff] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#00BAF2]">Invoice</p>
          <p className="mt-1 text-base font-bold text-[#002970]">{invoice.invoiceId}</p>
        </div>

        <p>
          Original invoice amount: <span className="font-semibold">{formatINR(invoice.amount)}</span>
        </p>
        <p>
          Advance amount: <span className="text-lg font-black text-[#002970]">{formatINR(offer.advanceAmount)}</span>
        </p>
        <p>
          Fee amount: <span className="font-semibold">{formatINR(feeAmount)}</span>
        </p>
        <p>
          Effective APR: <span className="font-semibold">{effectiveApr}%</span>
        </p>
        <p>Repayment trigger: {offer.repaymentTrigger}</p>

        <div className="rounded-xl border border-[#d5e1f5] bg-[#eef5ff] p-3 text-sm text-[#002970]">
          You receive: {formatINR(offer.advanceAmount)} today. You repay: {formatINR(repayAmount)} when buyer pays.
        </div>
      </div>
    </Modal>
  );
}
