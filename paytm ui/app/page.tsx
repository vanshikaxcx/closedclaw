import { Header } from '@/components/header';
import Link from 'next/link';
import {
  ArrowRight,
  Bus,
  CreditCard,
  FileText,
  Plane,
  ShieldCheck,
  Smartphone,
  Store,
  Train,
  Wallet,
  Zap,
} from 'lucide-react';

const consumerActions = [
  { label: 'Recharge', icon: Smartphone, href: '/recharge-bills#mobile' },
  { label: 'Pay Bills', icon: FileText, href: '/recharge-bills#electricity' },
  { label: 'Mobile', icon: Wallet, href: '/recharge-bills' },
  { label: 'DTH', icon: Zap, href: '/recharge-bills#dth' },
  { label: 'Electricity', icon: CreditCard, href: '/recharge-bills#electricity' },
  { label: 'Book Gas', icon: ShieldCheck, href: '/recharge-bills' },
];

const ticketActions = [
  { label: 'Flight Tickets', icon: Plane, href: '/ticket-booking#flights' },
  { label: 'Bus Tickets', icon: Bus, href: '/ticket-booking#bus' },
  { label: 'Train Tickets', icon: Train, href: '/ticket-booking#trains' },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#f4f8fe] text-slate-900">
      <Header />

      <main>
        <section className="container-paytm pt-8 sm:pt-10">
          <div className="rounded-[30px] bg-linear-to-r from-[#e8f6ff] via-white to-[#edf4ff] px-5 py-10 shadow-[0_14px_40px_rgba(4,47,114,0.08)] sm:px-10">
            <div className="grid gap-8 lg:grid-cols-2">
              <div>
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#c8d8f5] bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[#0a58d8]">
                  India&apos;s Payments Super App
                </div>
                <h1 className="max-w-xl text-4xl font-black leading-tight text-[#062a64] sm:text-5xl">
                  Recharge, pay bills, and grow your business on one trusted app.
                </h1>
                <p className="mt-4 max-w-xl text-base text-slate-600 sm:text-lg">
                  Consumer payments and merchant finance in one flow, now with demo-ready dashboards for judges and mentors.
                </p>
                <div className="mt-7 flex flex-wrap items-center gap-3">
                  <Link href="/login?demo=true" className="inline-flex items-center gap-2 rounded-xl bg-[#002970] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#0a3f9d]">
                    Try Merchant Demo
                    <ArrowRight size={16} />
                  </Link>
                  <Link href="/login" className="inline-flex items-center gap-2 rounded-xl border border-[#c7d8f3] bg-white px-5 py-3 text-sm font-bold text-[#0a58d8] transition hover:bg-[#edf5ff]">
                    Merchant/Admin Login
                  </Link>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[#00baf2]">Smart Collections</p>
                  <p className="mt-2 text-2xl font-black text-[#062a64]">₹3.2L</p>
                  <p className="mt-1 text-sm text-slate-600">Daily UPI inflow tracked live in merchant dashboard.</p>
                </div>
                <div className="rounded-2xl bg-white p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[#00baf2]">GST Health</p>
                  <p className="mt-2 text-2xl font-black text-[#062a64]">92%</p>
                  <p className="mt-1 text-sm text-slate-600">Filing confidence score updates after every action.</p>
                </div>
                <div className="rounded-2xl bg-white p-5 shadow-sm sm:col-span-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[#00baf2]">Credit Flywheel</p>
                  <p className="mt-2 text-base font-semibold text-[#062a64]">File GST → Improve trust score → Unlock invoice finance → Repay and repeat.</p>
                  <p className="mt-1 text-sm text-slate-600">Built as mock + live adapters so backend integrations can be swapped later.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="container-paytm mt-8">
          <div className="rounded-3xl bg-[#00baf2] px-5 py-8 text-white sm:px-8">
            <h2 className="text-2xl font-black sm:text-3xl">Recharge & Pay Bills on Paytm.</h2>
            <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {consumerActions.map((action) => (
                <Link key={action.label} href={action.href} className="group rounded-2xl bg-white/10 p-4 transition hover:bg-white/20">
                  <action.icon className="h-7 w-7" />
                  <p className="mt-3 text-sm font-semibold">{action.label}</p>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className="container-paytm mt-7">
          <div className="rounded-3xl bg-[#0f4a8a] px-5 py-8 text-white sm:px-8">
            <h2 className="text-2xl font-black sm:text-3xl">Book & Buy on Paytm.</h2>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              {ticketActions.map((action) => (
                <Link key={action.label} href={action.href} className="rounded-2xl bg-white/10 p-5 transition hover:bg-white/20">
                  <action.icon className="h-7 w-7" />
                  <p className="mt-3 text-sm font-semibold">{action.label}</p>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className="container-paytm mt-7 pb-12">
          <div className="rounded-3xl border border-[#d6e3f7] bg-white p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-[#00baf2]">Paytm for Business</p>
                <h2 className="mt-2 text-2xl font-black text-[#062a64] sm:text-3xl">Merchant cockpit for GST, trust score and invoice finance.</h2>
                <p className="mt-2 max-w-2xl text-sm text-slate-600 sm:text-base">
                  Explore the full merchant lifecycle with role-based dashboards, action toasts, audit trail, and admin overview.
                </p>
              </div>
              <Store className="h-9 w-9 text-[#0a58d8]" />
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/merchant" className="rounded-xl bg-[#002970] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#0a3f9d]">
                Open Merchant Hub
              </Link>
              <Link href="/admin/dashboard" className="rounded-xl border border-[#c7d8f3] bg-white px-5 py-3 text-sm font-bold text-[#0a58d8] transition hover:bg-[#edf5ff]">
                Open Admin Dashboard
              </Link>
              <Link href="/paytm-business" className="rounded-xl border border-[#c7d8f3] bg-white px-5 py-3 text-sm font-bold text-[#0a58d8] transition hover:bg-[#edf5ff]">
                Learn More
              </Link>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
