'use client';

import useSWR from 'swr';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useAuth } from '@/lib/auth-context';
import { adapter } from '@/src/adapters';
import { TrustScoreGauge } from '@/src/components/shared/TrustScoreGauge';

const tips = {
  paymentRate: 'Collect dues faster with reminder nudges.',
  consistency: 'Maintain stable transaction frequency weekly.',
  volumeTrend: 'Grow high-quality order volume month over month.',
  gstCompliance: 'File GST on time and keep flagged rows near zero.',
  returnRate: 'Reduce return/dispute rates with cleaner invoicing.',
};

const faq = [
  {
    q: 'How does payment rate affect score?',
    a: 'Timely buyer payments improve lender confidence and increase paymentRate weight in score computation.',
  },
  {
    q: 'Why does consistency matter?',
    a: 'Consistent daily transaction behavior is a strong indicator of stable business operations.',
  },
  {
    q: 'How is volume trend measured?',
    a: 'The model compares rolling 30-day and 90-day volume trajectories to reward sustained growth.',
  },
  {
    q: 'How does GST filing influence trust?',
    a: 'On-time and clean GST filing boosts compliance confidence and directly improves the GST component.',
  },
  {
    q: 'What can hurt my return rate component?',
    a: 'Frequent disputes, returns, and delayed resolution reduce reliability and pull score downward.',
  },
];

export default function MerchantTrustScorePage() {
  const { session } = useAuth();

  const { data } = useSWR(
    session?.merchantId ? (['merchant-trust', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      return adapter.getTrustScore(merchantId);
    },
  );

  if (!data) {
    return <div className="paytm-surface p-5 text-sm text-slate-600">Loading TrustScore...</div>;
  }

  const compCards = [
    { key: 'paymentRate', label: 'Payment Rate', value: data.components.paymentRate, max: 30 },
    { key: 'consistency', label: 'Consistency', value: data.components.consistency, max: 20 },
    { key: 'volumeTrend', label: 'Volume Trend', value: data.components.volumeTrend, max: 20 },
    { key: 'gstCompliance', label: 'GST Compliance', value: data.components.gstCompliance, max: 20 },
    { key: 'returnRate', label: 'Return Rate', value: data.components.returnRate, max: 10 },
  ] as const;

  return (
    <div className="space-y-4">
      <section className="paytm-surface p-6 text-center">
        <TrustScoreGauge trustScore={data} size={300} />
        <p className="mt-2 text-sm text-slate-600">
          {data.bucket} - You're trusted by lenders. Keep filing GST on time to reach Excellent.
        </p>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        {compCards.map((card, index) => {
          const width = Math.max(4, Math.min(100, (card.value / card.max) * 100));
          return (
            <article key={card.key} className={`paytm-surface p-5 ${index === 4 ? 'md:col-span-2 md:mx-auto md:max-w-md' : ''}`}>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-[#002970]">{card.label}</h3>
                <span className="text-sm font-semibold text-slate-700">
                  {card.value}/{card.max}
                </span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-100">
                <div className="h-2 rounded-full bg-[#00BAF2]" style={{ width: `${width}%` }} />
              </div>
              <p className="mt-2 text-xs text-slate-600">{tips[card.key]}</p>
            </article>
          );
        })}
      </section>

      <section className="paytm-surface p-5">
        <h3 className="text-lg font-black text-[#002970]">Score History (90 days)</h3>
        <div className="mt-3 h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.history}>
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748b' }} />
              <Tooltip />
              <Line type="monotone" dataKey="score" stroke="#00BAF2" strokeWidth={2.5} dot={{ r: 2.5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="paytm-surface p-5">
        <h3 className="text-lg font-black text-[#002970]">What affects my score?</h3>
        <div className="mt-3 space-y-2">
          {faq.map((item) => (
            <details key={item.q} className="rounded-xl border border-[#dde6f5] bg-white p-3">
              <summary className="cursor-pointer text-sm font-semibold text-slate-800">{item.q}</summary>
              <p className="mt-2 text-sm text-slate-600">{item.a}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
