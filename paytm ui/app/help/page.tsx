import Link from 'next/link';
import { Header } from '@/components/header';

export default function HelpPage() {
  return (
    <div className="min-h-screen bg-[#f4f8fe]">
      <Header />
      <main className="container-paytm py-8">
        <section className="paytm-surface p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0a58d8]">Support</p>
          <h1 className="mt-3 text-3xl font-black text-[#062a64]">Help Center</h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-600">
            For demo support, use the merchant credentials listed on the login page. This build runs in mock-first mode with optional live adapter fallback.
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-[#dbe1ec] bg-white p-4">
              <p className="text-sm font-bold text-slate-900">Merchant Demo</p>
              <p className="mt-1 text-xs text-slate-600">Open /login?demo=true to auto-seed judging data and run auto-flow.</p>
            </div>
            <div className="rounded-2xl border border-[#dbe1ec] bg-white p-4">
              <p className="text-sm font-bold text-slate-900">Admin Review</p>
              <p className="mt-1 text-xs text-slate-600">Use admin_arth / 9999 to inspect merchant portfolio and flywheel health.</p>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/login" className="rounded-xl bg-[#002970] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#0a3f9d]">
              Open Login
            </Link>
            <Link href="/merchant/dashboard" className="rounded-xl border border-[#bfd3f2] px-5 py-2.5 text-sm font-bold text-[#0a58d8] hover:bg-[#edf5ff]">
              Merchant Dashboard
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
