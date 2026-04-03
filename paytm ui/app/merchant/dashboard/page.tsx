'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import useSWR from 'swr';
import { Button } from '@/components/ui/button';
import { adapter } from '@/src/adapters';
import type { AuditEntry, GSTDraft, Invoice, Notification, TrustScore, WalletBalance } from '@/src/adapters/types';
import { DataTable, LoadingSkeleton, MetricCard, StatusBadge } from '@/src/components/ui';
import { CashflowChart } from '@/src/components/shared/CashflowChart';
import { FlywheelCard } from '@/src/components/shared/FlywheelCard';
import { TrustScoreGauge } from '@/src/components/shared/TrustScoreGauge';
import { useAuth } from '@/lib/auth-context';
import { useToast } from '@/src/context/toast-context';
import { DEMO_WHATSAPP_PHONE, WHATSAPP_TEMPLATES } from '@/src/lib/whatsapp-templates';
import { formatDateTime, formatINR } from '@/src/lib/format';

type DashboardSettled<T> = PromiseSettledResult<T>;

interface DashboardData {
  wallet: DashboardSettled<WalletBalance>;
  cashflow: DashboardSettled<{ projection: any; history: any[] }>;
  gstDraft: DashboardSettled<GSTDraft>;
  trustScore: DashboardSettled<TrustScore>;
  invoices: DashboardSettled<Invoice[]>;
  notifications: DashboardSettled<Notification[]>;
  audit: DashboardSettled<AuditEntry[]>;
}

interface CoachStep {
  key: string;
  message: string;
}

const coachSteps: CoachStep[] = [
  { key: 'trust', message: 'Your credit reputation score built from real transaction behavior.' },
  { key: 'gst', message: '847 transactions auto-categorised. 3 need your review.' },
  { key: 'flywheel', message: 'Every action here compounds your financial position.' },
  { key: 'actions', message: 'All critical actions are one tap away.' },
];

function successResult<T>(result: DashboardSettled<T>): T | null {
  return result.status === 'fulfilled' ? result.value : null;
}

export default function MerchantDashboardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session, isDemoMode, startDemoMode } = useAuth();
  const toast = useToast();

  const [windowDays, setWindowDays] = useState<30 | 60 | 90>(30);
  const [dismissStockAlert, setDismissStockAlert] = useState(false);
  const [coachIndex, setCoachIndex] = useState<number | null>(null);
  const [autoNarration, setAutoNarration] = useState<string | null>(null);

  const trustRef = useRef<HTMLDivElement | null>(null);
  const gstRef = useRef<HTMLDivElement | null>(null);
  const flywheelRef = useRef<HTMLDivElement | null>(null);
  const actionsRef = useRef<HTMLDivElement | null>(null);

  const { data, isLoading, mutate } = useSWR<DashboardData>(
    session?.merchantId ? (['merchant-dashboard', session.merchantId] as const) : null,
    async (key: readonly [string, string]) => {
      const merchantId = key[1];
      const [wallet, cashflow, gstDraft, trustScore, invoices, notifications, audit] = await Promise.allSettled([
        adapter.getWalletBalance(merchantId),
        adapter.getCashflow(merchantId),
        adapter.getGSTDraft(merchantId),
        adapter.getTrustScore(merchantId),
        adapter.getInvoices(merchantId),
        adapter.getNotifications(merchantId),
        adapter.getAuditLog(merchantId),
      ]);

      return {
        wallet,
        cashflow,
        gstDraft,
        trustScore,
        invoices,
        notifications,
        audit,
      };
    },
    {
      refreshInterval: 30000,
      revalidateOnFocus: false,
    },
  );

  const wallet = data ? successResult(data.wallet) : null;
  const cashflow = data ? successResult(data.cashflow) : null;
  const gstDraft = data ? successResult(data.gstDraft) : null;
  const trustScore = data ? successResult(data.trustScore) : null;
  const invoices = data ? successResult(data.invoices) ?? [] : [];
  const notifications = data ? successResult(data.notifications) ?? [] : [];
  const auditLog = data ? successResult(data.audit) ?? [] : [];

  const overdueCount = invoices.filter((row) => row.status === 'OVERDUE').length;
  const pendingCount = invoices.filter((row) => row.status === 'PENDING' || row.status === 'OVERDUE').length;
  const todayRevenue = cashflow?.history.at(-1)?.amount ?? 0;
  const trustChange30 = trustScore ? trustScore.score - (trustScore.history.at(-30)?.score ?? trustScore.score) : 0;
  const walletDelta = cashflow?.history.length
    ? cashflow.history.at(-1)!.amount - (cashflow.history.at(-2)?.amount ?? cashflow.history.at(-1)!.amount)
    : 0;

  const stockAlertMessage =
    !dismissStockAlert && cashflow && cashflow.projection.p30.amount > 420000
      ? `Stock reorder window detected. Expected inflow this week: ${formatINR(Math.round(cashflow.projection.p30.amount / 4))}.`
      : undefined;

  useEffect(() => {
    if (!isDemoMode || !session || coachIndex !== null) {
      return;
    }

    const viewed = window.localStorage.getItem('merchant_coach_completed');
    if (!viewed || searchParams.get('tour') === 'demo') {
      setCoachIndex(0);
    }
  }, [coachIndex, isDemoMode, searchParams, session]);

  const runDemoAutoActions = async () => {
    if (!session?.merchantId) {
      return;
    }

    setAutoNarration('Dashboard overview');
    await new Promise((resolve) => setTimeout(resolve, 900));
    setAutoNarration('GST review and filing');
    await adapter.fileGST(session.merchantId);

    setAutoNarration('TrustScore refresh');
    await mutate();

    const latestInvoices = await adapter.getInvoices(session.merchantId);
    const overdue = latestInvoices.find((row) => row.status === 'OVERDUE');

    if (overdue) {
      setAutoNarration('Invoice financing acceptance');
      const offer = await adapter.requestCreditOffer(session.merchantId, overdue.invoiceId);
      await adapter.acceptCreditOffer(session.merchantId, offer.offerId);
      toast.whatsapp(
        WHATSAPP_TEMPLATES.invoiceAdvanceAccepted({
          amount: offer.advanceAmount,
          invoiceId: overdue.invoiceId,
          buyerName: overdue.buyerName,
        }),
        DEMO_WHATSAPP_PHONE,
      );
    }

    setAutoNarration('Audit proof chain ready');
    await mutate();
    window.setTimeout(() => setAutoNarration(null), 1800);
    router.push('/merchant/audit');
  };

  if (!session?.merchantId) {
    return (
      <div className="paytm-surface p-6">
        <p className="text-sm text-slate-600">Merchant session not found.</p>
        <Link href="/login" className="mt-3 inline-flex rounded-full bg-[#002970] px-4 py-2 text-sm font-semibold text-white">
          Go to Login
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-20">
      <section className="paytm-surface p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Merchant Dashboard</p>
            <h2 className="mt-2 text-2xl font-black text-[#002970]">Ramesh General Store</h2>
            <p className="mt-1 text-sm text-slate-600">PayBot to GST to TrustScore to Invoice Finance to CashFlow.</p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" className="rounded-full" onClick={() => void startDemoMode()}>
              Reset Demo
            </Button>
            <Button className="rounded-full bg-[#002970] hover:bg-[#0a3f9d]" onClick={() => void runDemoAutoActions()}>
              Start Guided Tour
            </Button>
          </div>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div>
          {isLoading && !wallet ? (
            <LoadingSkeleton variant="metric" />
          ) : wallet ? (
            <MetricCard
              label="Wallet Balance"
              value={formatINR(wallet.balance)}
              trend={walletDelta >= 0 ? 'up' : 'down'}
              trendValue={`${formatINR(Math.abs(walletDelta))} vs yesterday`}
              onClick={() => router.push('/merchant/wallet')}
            />
          ) : (
            <div className="paytm-surface p-5 text-sm text-red-600">Wallet data unavailable</div>
          )}
        </div>

        <div>
          {isLoading && !cashflow ? (
            <LoadingSkeleton variant="metric" />
          ) : cashflow ? (
            <MetricCard
              label="Today's Revenue"
              value={formatINR(todayRevenue)}
              trend="up"
              trendValue="Live from cashflow"
              onClick={() => router.push('/merchant/cashflow')}
            />
          ) : (
            <div className="paytm-surface p-5 text-sm text-red-600">Cashflow data unavailable</div>
          )}
        </div>

        <div ref={trustRef}>
          {isLoading && !trustScore ? (
            <LoadingSkeleton variant="metric" />
          ) : trustScore ? (
            <MetricCard
              label="TrustScore"
              value={trustScore.score}
              sublabel={trustScore.bucket}
              trend={trustChange30 >= 0 ? 'up' : 'down'}
              trendValue={`${trustChange30 >= 0 ? '+' : ''}${trustChange30} in 30 days`}
              onClick={() => router.push('/merchant/trust-score')}
            />
          ) : (
            <div className="paytm-surface p-5 text-sm text-red-600">TrustScore unavailable</div>
          )}
        </div>

        <div>
          {isLoading && !data ? (
            <LoadingSkeleton variant="metric" />
          ) : (
            <MetricCard
              label="Pending Invoices"
              value={pendingCount}
              sublabel={overdueCount > 0 ? `${overdueCount} overdue` : 'No overdue'}
              trend={overdueCount > 0 ? 'down' : 'neutral'}
              trendValue={overdueCount > 0 ? 'Collections attention required' : 'Healthy cycle'}
              onClick={() => router.push('/merchant/invoices')}
            />
          )}
        </div>
      </section>

      {cashflow ? (
        <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <article className="paytm-surface p-5 sm:p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#00BAF2]">Projection Snapshots</p>
            <div className="mt-3 space-y-2">
              <MetricCard label="p30" value={formatINR(cashflow.projection.p30.amount)} sublabel={`${cashflow.projection.p30.confidence}% confidence`} />
              <MetricCard label="p60" value={formatINR(cashflow.projection.p60.amount)} sublabel={`${cashflow.projection.p60.confidence}% confidence`} />
              <MetricCard label="p90" value={formatINR(cashflow.projection.p90.amount)} sublabel={`${cashflow.projection.p90.confidence}% confidence`} />
            </div>
          </article>
          <CashflowChart
            history={cashflow.history}
            projection={cashflow.projection}
            windowDays={windowDays}
            onWindowChange={setWindowDays}
            stockAlertMessage={stockAlertMessage}
            onDismissAlert={() => setDismissStockAlert(true)}
          />
        </section>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-2">
        <article ref={gstRef} className="paytm-surface p-5 sm:p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-black text-[#002970]">GST Status</h3>
            {gstDraft ? <StatusBadge status={gstDraft.summary.flaggedCount > 0 ? 'FLAGGED' : 'FILED'} /> : null}
          </div>
          {gstDraft ? (
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p>
                Quarter: {gstDraft.quarter} {gstDraft.year}
              </p>
              <p>Auto-categorised: {gstDraft.summary.totalCount - gstDraft.summary.flaggedCount}</p>
              <p>Flagged: {gstDraft.summary.flaggedCount}</p>
              <p>Total tax liability: {formatINR(gstDraft.summary.netLiability)}</p>
              <Button onClick={() => router.push('/merchant/gst/review')} className="mt-2 rounded-full bg-[#002970] hover:bg-[#0a3f9d]">
                Review & File
              </Button>
            </div>
          ) : (
            <p className="mt-2 text-sm text-red-600">GST data unavailable.</p>
          )}
        </article>

        <TrustScoreGauge trustScore={trustScore ?? { score: 0, bucket: 'Low', components: { paymentRate: 0, consistency: 0, volumeTrend: 0, gstCompliance: 0, returnRate: 0 }, history: [], lastUpdated: new Date().toISOString() }} />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="paytm-surface p-5 sm:p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-black text-[#002970]">Recent Invoices</h3>
            <Link href="/merchant/invoices" className="text-sm font-semibold text-[#0a58d8]">
              View All Invoices
            </Link>
          </div>

          <div className="mt-3">
            <DataTable
              columns={[
                { key: 'invoiceId', header: 'Invoice' },
                { key: 'buyerName', header: 'Buyer' },
                { key: 'amount', header: 'Amount', render: (value) => formatINR(Number(value)) },
                {
                  key: 'status',
                  header: 'Status',
                  render: (value) => <StatusBadge status={String(value) as any} />,
                },
              ]}
                data={invoices.slice(0, 3) as unknown as Record<string, unknown>[]}
            />
          </div>
        </article>

        <div ref={flywheelRef}>
          <FlywheelCard />
          <article className="paytm-surface mt-4 p-5">
            <p className="text-sm font-semibold text-slate-800">Recent Notifications</p>
            <div className="mt-2 space-y-2">
              {notifications.slice(0, 2).map((notification) => (
                <div key={notification.notifId} className="rounded-xl border border-[#e4eaf6] bg-white p-3">
                  <p className="text-sm font-semibold text-slate-800">{notification.title}</p>
                  <p className="text-xs text-slate-600">{notification.body}</p>
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section ref={actionsRef} className="sticky bottom-16 z-30 rounded-2xl border border-[#d7e0f0] bg-white/95 p-3 shadow-sm backdrop-blur lg:bottom-4">
        <div className="grid gap-2 sm:grid-cols-4">
          <Button variant="outline" className="rounded-full" onClick={() => router.push('/merchant/transfers')}>
            Transfer Money
          </Button>
          <Button variant="outline" className="rounded-full" onClick={() => router.push('/merchant/gst/review')}>
            File GST
          </Button>
          <Button variant="outline" className="rounded-full" onClick={() => router.push('/merchant/finance/offers')}>
            View Offers
          </Button>
          <Button
            className="rounded-full bg-[#002970] hover:bg-[#0a3f9d]"
            onClick={async () => {
              if (!cashflow) {
                return;
              }
              const message = WHATSAPP_TEMPLATES.stockReorderAlert({
                amount: Math.round(cashflow.projection.p30.amount / 4),
              });
              await adapter.sendWhatsappAlert({
                merchantId: session.merchantId!,
                phone: DEMO_WHATSAPP_PHONE,
                message,
              });
              toast.whatsapp(message, DEMO_WHATSAPP_PHONE);
            }}
          >
            Send WhatsApp Alert
          </Button>
        </div>
      </section>

      <section className="paytm-surface p-4">
        <p className="text-sm font-semibold text-slate-800">Latest Audit Entries</p>
        <div className="mt-2 space-y-2">
          {auditLog.slice(0, 5).map((entry) => (
            <div key={entry.logId} className="rounded-xl border border-[#e4eaf6] bg-white p-3">
              <p className="text-sm font-semibold text-slate-800">{entry.action.replace(/_/g, ' ')}</p>
              <p className="text-xs text-slate-500">{formatDateTime(entry.timestamp)}</p>
            </div>
          ))}
        </div>
      </section>

      {coachIndex !== null ? (
        <div className="fixed left-1/2 top-16 z-[110] -translate-x-1/2 rounded-full border border-[#d7e2f5] bg-white px-4 py-2 shadow">
          <p className="text-xs font-semibold text-[#002970]">{coachSteps[coachIndex].message}</p>
          <button
            type="button"
            className="mt-1 w-full text-[11px] font-bold uppercase tracking-[0.1em] text-[#0a58d8]"
            onClick={() => {
              if (coachIndex === coachSteps.length - 1) {
                setCoachIndex(null);
                window.localStorage.setItem('merchant_coach_completed', '1');
                toast.success('Dashboard tour complete. Try filing your GST return next.');
                return;
              }
              setCoachIndex((current) => (current === null ? 0 : current + 1));
            }}
          >
            Got it
          </button>
        </div>
      ) : null}

      {autoNarration ? (
        <div className="fixed left-1/2 top-4 z-[120] -translate-x-1/2 rounded-full bg-[#002970] px-4 py-2 text-xs font-semibold text-white shadow">
          {autoNarration}
        </div>
      ) : null}
    </div>
  );
}
