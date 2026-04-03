import { ArrowRight } from 'lucide-react';

const nodes = [
  { label: 'PayBot', color: 'bg-sky-100 text-sky-700' },
  { label: 'GST', color: 'bg-emerald-100 text-emerald-700' },
  { label: 'TrustScore', color: 'bg-amber-100 text-amber-700' },
  { label: 'Invoice Finance', color: 'bg-red-100 text-red-700' },
  { label: 'CashFlow Brain', color: 'bg-slate-100 text-slate-700' },
];

export function FlywheelCard() {
  return (
    <article className="rounded-2xl border border-[#d8e2f4] bg-[#f3f8ff] p-5">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#00BAF2]">Flywheel</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {nodes.map((node, index) => (
          <div key={node.label} className="flex items-center gap-2">
            <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${node.color}`}>{node.label}</span>
            {index < nodes.length - 1 ? <ArrowRight size={14} className="text-slate-400" /> : null}
          </div>
        ))}
      </div>
      <p className="mt-3 text-sm text-slate-600">Every transaction compounds your financial reputation.</p>
    </article>
  );
}
