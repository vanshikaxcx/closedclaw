'use client';

import { useMemo, useState } from 'react';
import useSWR from 'swr';
import { Button } from '@/components/ui/button';
import { adapter } from '@/src/adapters';
import { useAuth } from '@/src/context/auth-context';
import { useToast } from '@/src/context/toast-context';
import { initials } from '@/src/lib/format';

export default function MerchantProfilePage() {
  const { session } = useAuth();
  const toast = useToast();

  const { data, mutate } = useSWR(
    session?.merchantId ? (['merchant-profile', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      return adapter.getMerchantProfile(merchantId);
    },
  );

  const [editing, setEditing] = useState(false);
  const [businessName, setBusinessName] = useState('');
  const [category, setCategory] = useState('');
  const [phone, setPhone] = useState('');

  const canSave = useMemo(
    () => businessName.trim().length > 2 && category.trim().length > 1 && phone.trim().length > 8,
    [businessName, category, phone],
  );

  const startEdit = () => {
    if (!data) {
      return;
    }
    setBusinessName(data.businessName);
    setCategory(data.category);
    setPhone(data.phone);
    setEditing(true);
  };

  const saveChanges = async () => {
    if (!canSave) {
      toast.warning('Fill all required profile fields.');
      return;
    }

    toast.warning('Profile update API will be enabled in live adapter mode.');
    setEditing(false);
    await mutate();
  };

  if (!data) {
    return <div className="paytm-surface p-5 text-sm text-slate-600">Loading profile...</div>;
  }

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[#002970] text-base font-bold text-white">
              {initials(data.name)}
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Merchant Profile</p>
              <h1 className="text-2xl font-black text-[#002970]">{data.name}</h1>
              <p className="text-sm text-slate-600">Merchant ID: {data.merchantId}</p>
            </div>
          </div>

          {!editing ? (
            <Button onClick={startEdit} className="rounded-full bg-[#002970] px-5 text-white hover:bg-[#0a3f9d]">
              Edit Profile
            </Button>
          ) : (
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setEditing(false)} className="rounded-full">
                Cancel
              </Button>
              <Button onClick={() => void saveChanges()} className="rounded-full bg-[#002970] text-white hover:bg-[#0a3f9d]">
                Save
              </Button>
            </div>
          )}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="paytm-surface p-5">
          <h2 className="text-lg font-black text-[#002970]">Business Details</h2>
          <div className="mt-4 space-y-3">
            <label className="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              Business Name
              <input
                value={editing ? businessName : data.businessName}
                onChange={(event) => setBusinessName(event.target.value)}
                className="mt-1 h-10 w-full rounded-xl border border-[#d1daea] px-3 text-sm outline-none focus:border-[#00BAF2]"
                disabled={!editing}
              />
            </label>

            <label className="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              Category
              <input
                value={editing ? category : data.category}
                onChange={(event) => setCategory(event.target.value)}
                className="mt-1 h-10 w-full rounded-xl border border-[#d1daea] px-3 text-sm outline-none focus:border-[#00BAF2]"
                disabled={!editing}
              />
            </label>

            <label className="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              GSTIN
              <input
                value={data.gstin}
                className="mt-1 h-10 w-full rounded-xl border border-[#d1daea] bg-slate-50 px-3 text-sm text-slate-500"
                disabled
              />
            </label>
          </div>
        </article>

        <article className="paytm-surface p-5">
          <h2 className="text-lg font-black text-[#002970]">Account and KYC</h2>
          <div className="mt-4 space-y-3">
            <label className="block text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              Registered Phone
              <input
                value={editing ? phone : data.phone}
                onChange={(event) => setPhone(event.target.value)}
                className="mt-1 h-10 w-full rounded-xl border border-[#d1daea] px-3 text-sm outline-none focus:border-[#00BAF2]"
                disabled={!editing}
              />
            </label>

            <div className="rounded-xl border border-[#d1daea] bg-[#f8fbff] p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">KYC Status</p>
              <p className="mt-1 text-sm font-bold text-[#002970]">{data.kycStatus.toUpperCase()}</p>
              <p className="mt-2 text-xs text-slate-600">
                KYC documents are locked in demo mode to preserve consistency for judges.
              </p>
            </div>

            <div className="rounded-xl border border-[#d1daea] bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Security</p>
              <p className="mt-1 text-sm text-slate-700">UPI PIN and session timeout are active for sensitive actions.</p>
            </div>
          </div>
        </article>
      </section>
    </div>
  );
}
