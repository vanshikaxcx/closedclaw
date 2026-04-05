import type {
  AdapterInterface,
  AuditEntry,
  AuthResult,
  CashflowProjection,
  CreditOffer,
  DailyRevenue,
  GSTDraft,
  GSTTransaction,
  GSTTransactionPatch,
  Invoice,
  Merchant,
  Notification,
  RegisterAccountInput,
  SendWhatsappAlertInput,
  Transfer,
  TransferInput,
  TrustScore,
  UserRole,
  UserSession,
  WalletBalance,
} from "@/src/adapters/types";

interface MerchantRuntime {
  role: UserRole;
  profile: Merchant;
  wallet: WalletBalance;
  cashflowHistory: DailyRevenue[];
  cashflowProjection: CashflowProjection;
  gstDraft: GSTDraft;
  trustScore: TrustScore;
  invoices: Invoice[];
  offers: CreditOffer[];
  notifications: Notification[];
  auditLog: AuditEntry[];
  transfers: Transfer[];
  pinHash: string;
}

interface MockState {
  merchants: Record<string, MerchantRuntime>;
  whatsappLog: Array<{ phone: string; message: string; timestamp: string }>;
  counters: {
    audit: number;
    transfer: number;
    offer: number;
    filing: number;
    notification: number;
  };
}

const INR = "INR";
const DEMO_PHONE = "+91-98765-43210";
const DEMO_MERCHANT_ID = "seller_a";
const ADMIN_MERCHANT_ID = "admin_hq";

const PIN_HASH_1234 = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4";
const PIN_HASH_9999 = "888df25ae35772424e2fcbf7ffb9c7f1f5e20a8f6f1d7f76f28fd00a355b0f7e";

function nowISO(): string {
  return new Date().toISOString();
}

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function mulberry32(seed: number) {
  return function next() {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function getTrustBucket(score: number): TrustScore["bucket"] {
  if (score <= 40) {
    return "Low";
  }
  if (score <= 65) {
    return "Medium";
  }
  if (score <= 80) {
    return "Good";
  }
  return "Excellent";
}

function buildTrustHistory(days = 90): Array<{ date: string; score: number }> {
  const points: Array<{ date: string; score: number }> = [];
  const start = new Date();
  start.setDate(start.getDate() - (days - 1));

  for (let i = 0; i < days; i += 1) {
    const date = new Date(start);
    date.setDate(start.getDate() + i);
    const growth = Math.floor((i / (days - 1)) * 12);
    const score = Math.min(74, 62 + growth + (i % 9 === 0 ? 1 : 0));

    points.push({
      date: date.toISOString().slice(0, 10),
      score,
    });
  }

  points[points.length - 1] = {
    ...points[points.length - 1],
    score: 74,
  };

  return points;
}

function buildDailyRevenue(days = 180): DailyRevenue[] {
  const rng = mulberry32(20260403);
  const list: DailyRevenue[] = [];
  const start = new Date();
  start.setDate(start.getDate() - (days - 1));

  for (let i = 0; i < days; i += 1) {
    const date = new Date(start);
    date.setDate(start.getDate() + i);

    const seasonal = 1 + Math.sin(i / 7) * 0.08;
    const trend = 1 + i / 850;
    const base = 18000 * seasonal * trend;
    const jitter = 1 + (rng() - 0.5) * 0.16;
    const amount = Math.max(8500, Math.round(base * jitter));

    list.push({
      date: date.toISOString().slice(0, 10),
      amount,
      transactionCount: Math.max(45, Math.round(amount / 320 + rng() * 22)),
      isProjected: false,
      lowerBound: round2(amount * 0.9),
      upperBound: round2(amount * 1.1),
    });
  }

  return list;
}

function buildProjection(history: DailyRevenue[]): CashflowProjection {
  const recent = history.slice(-30);
  const avg = recent.reduce((sum, point) => sum + point.amount, 0) / Math.max(1, recent.length);

  return {
    p30: {
      amount: Math.round(avg * 30 * 1.02),
      confidence: 88,
    },
    p60: {
      amount: Math.round(avg * 60 * 1.03),
      confidence: 83,
    },
    p90: {
      amount: Math.round(avg * 90 * 1.05),
      confidence: 78,
    },
    generatedAt: nowISO(),
  };
}

function buildGSTTransactions(count = 847): GSTTransaction[] {
  const rng = mulberry32(847);
  const rates = [0, 0.05, 0.12, 0.18];
  const categories: GSTTransaction["category"][] = ["B2B", "B2C_LOCAL", "B2C_INTERSTATE", "EXEMPT"];
  const descriptions = [
    "PayBot POS grocery order",
    "Bulk rice and pulses sale",
    "Dairy and frozen goods retail",
    "Snack packet wholesale",
    "Household staples mixed basket",
  ];

  const rows: GSTTransaction[] = [];

  for (let i = 1; i <= count; i += 1) {
    const amount = Math.round(700 + rng() * 7800);
    const gstRate = rates[Math.floor(rng() * rates.length)];
    const category = categories[Math.floor(rng() * categories.length)];
    const taxableRate = category === "EXEMPT" ? 0 : gstRate;
    const cgst = taxableRate === 0 ? 0 : round2((amount * taxableRate) / 2);
    const sgst = taxableRate === 0 ? 0 : round2((amount * taxableRate) / 2);

    rows.push({
      txId: `GST-${String(i).padStart(4, "0")}`,
      description: `${descriptions[i % descriptions.length]} #${i}`,
      amount,
      hsnCode: `${10000000 + (i % 999999)}`,
      gstRate: taxableRate,
      cgst,
      sgst,
      category,
      reviewFlag: false,
      editedByUser: false,
    });
  }

  // Mark exactly 3 rows as flagged.
  const flaggedIds = [count - 2, count - 1, count];
  flaggedIds.forEach((index, offset) => {
    const row = rows[index - 1];
    row.reviewFlag = true;
    row.gstRate = [0.05, 0.12, 0.18][offset];
    row.cgst = round2((row.amount * row.gstRate) / 2);
    row.sgst = round2((row.amount * row.gstRate) / 2);
    row.hsnCode = ["99999999", "88888888", "77777777"][offset];
  });

  return rows;
}

function summarizeGST(transactions: GSTTransaction[]): GSTDraft["summary"] {
  const totalTaxable = transactions.reduce((sum, row) => sum + row.amount, 0);
  const totalCGST = transactions.reduce((sum, row) => sum + row.cgst, 0);
  const totalSGST = transactions.reduce((sum, row) => sum + row.sgst, 0);
  const flaggedCount = transactions.filter((row) => row.reviewFlag).length;

  return {
    totalTaxable: round2(totalTaxable),
    totalCGST: round2(totalCGST),
    totalSGST: round2(totalSGST),
    netLiability: round2(totalCGST + totalSGST),
    flaggedCount,
    totalCount: transactions.length,
  };
}

function buildRameshInvoices(): Invoice[] {
  const baseDate = new Date();
  const daysAgo = (days: number) => {
    const date = new Date(baseDate);
    date.setDate(date.getDate() - days);
    return date.toISOString();
  };

  return [
    {
      invoiceId: "INV-041",
      buyerName: "Aggarwal Foods Pvt Ltd",
      buyerGstin: "06AACCA1111A1Z5",
      amount: 12400,
      dueDate: daysAgo(5),
      status: "PAID",
      overdueDays: 0,
      advanceAmount: 0,
      feeRate: 0,
      repaid: true,
      createdAt: daysAgo(28),
    },
    {
      invoiceId: "INV-042",
      buyerName: "Metro Fresh Retail LLP",
      buyerGstin: "07AAGCM2222B1ZY",
      amount: 18600,
      dueDate: daysAgo(2),
      status: "PAID",
      overdueDays: 0,
      advanceAmount: 0,
      feeRate: 0,
      repaid: true,
      createdAt: daysAgo(25),
    },
    {
      invoiceId: "INV-043",
      buyerName: "Lakshmi Provisions",
      buyerGstin: "07BBCCP3333K1Z1",
      amount: 21200,
      dueDate: daysAgo(-4),
      status: "PENDING",
      overdueDays: 0,
      advanceAmount: 0,
      feeRate: 0,
      repaid: false,
      createdAt: daysAgo(18),
    },
    {
      invoiceId: "INV-044",
      buyerName: "Sharma Electronics Pvt Ltd",
      buyerGstin: "07AAVCS4444Q1ZA",
      amount: 28500,
      dueDate: daysAgo(18),
      status: "OVERDUE",
      overdueDays: 18,
      advanceAmount: 0,
      feeRate: 0,
      repaid: false,
      createdAt: daysAgo(34),
    },
    {
      invoiceId: "INV-045",
      buyerName: "Naina Traders",
      buyerGstin: "07AAGTN5555L1ZX",
      amount: 31600,
      dueDate: daysAgo(21),
      status: "FINANCED",
      overdueDays: 0,
      advanceAmount: 25280,
      feeRate: 1.8,
      repaid: false,
      createdAt: daysAgo(41),
    },
  ];
}

function buildRameshNotifications(): Notification[] {
  return [
    {
      notifId: "NOTIF-001",
      type: "gst",
      title: "GST draft generated",
      body: "847 transactions auto-categorised. 3 need review before filing.",
      read: false,
      timestamp: nowISO(),
      actionUrl: "/merchant/gst/review",
    },
    {
      notifId: "NOTIF-002",
      type: "invoice",
      title: "Overdue invoice detected",
      body: "INV-044 is overdue by 18 days and eligible for finance.",
      read: false,
      timestamp: nowISO(),
      actionUrl: "/merchant/invoices",
    },
    {
      notifId: "NOTIF-003",
      type: "finance",
      title: "Offer pre-check complete",
      body: "Advance up to Rs. 24,225 available on INV-044.",
      read: true,
      timestamp: nowISO(),
      actionUrl: "/merchant/finance/offers",
    },
    {
      notifId: "NOTIF-004",
      type: "alert",
      title: "Reorder window soon",
      body: "Projected inflow for next week supports a fresh stock cycle.",
      read: true,
      timestamp: nowISO(),
      actionUrl: "/merchant/cashflow",
    },
    {
      notifId: "NOTIF-005",
      type: "transfer",
      title: "Wallet updated",
      body: "Latest disbursal and transfer entries are reflected in wallet history.",
      read: true,
      timestamp: nowISO(),
      actionUrl: "/merchant/wallet",
    },
  ];
}

function buildRameshAuditEntries(): AuditEntry[] {
  const now = new Date();
  const fromMinutes = (mins: number) => {
    const ts = new Date(now);
    ts.setMinutes(now.getMinutes() - mins);
    return ts.toISOString();
  };

  return [
    {
      logId: "AUD-001",
      timestamp: fromMinutes(320),
      actorType: "system",
      actorId: "seed-engine",
      action: "demo_seed_initialized",
      entityId: DEMO_MERCHANT_ID,
      outcome: "success",
      metadata: { rows: 847, invoices: 5, trustScore: 74 },
    },
    {
      logId: "AUD-002",
      timestamp: fromMinutes(290),
      actorType: "merchant",
      actorId: DEMO_MERCHANT_ID,
      action: "dashboard_opened",
      entityId: "merchant/dashboard",
      outcome: "success",
      metadata: { mode: "demo" },
    },
    {
      logId: "AUD-003",
      timestamp: fromMinutes(260),
      actorType: "merchant",
      actorId: DEMO_MERCHANT_ID,
      action: "invoice_viewed",
      entityId: "INV-044",
      amount: 28500,
      outcome: "success",
      metadata: { status: "OVERDUE" },
    },
    {
      logId: "AUD-004",
      timestamp: fromMinutes(240),
      actorType: "merchant",
      actorId: DEMO_MERCHANT_ID,
      action: "cashflow_projection_checked",
      entityId: "cashflow:p30",
      outcome: "success",
      metadata: { confidence: 88 },
    },
    {
      logId: "AUD-005",
      timestamp: fromMinutes(210),
      actorType: "merchant",
      actorId: DEMO_MERCHANT_ID,
      action: "notification_opened",
      entityId: "NOTIF-002",
      outcome: "success",
      metadata: { source: "invoice" },
    },
    {
      logId: "AUD-006",
      timestamp: fromMinutes(180),
      actorType: "system",
      actorId: "forecast-service",
      action: "stock_alert_generated",
      entityId: DEMO_MERCHANT_ID,
      outcome: "success",
      metadata: { expectedInflowWeek: 138400 },
    },
    {
      logId: "AUD-007",
      timestamp: fromMinutes(145),
      actorType: "merchant",
      actorId: DEMO_MERCHANT_ID,
      action: "gst_review_started",
      entityId: "Q1-2026",
      outcome: "success",
      metadata: { flaggedCount: 3 },
    },
    {
      logId: "AUD-008",
      timestamp: fromMinutes(122),
      actorType: "merchant",
      actorId: DEMO_MERCHANT_ID,
      action: "gst_tx_flagged",
      entityId: "GST-0847",
      outcome: "pending",
      metadata: { reason: "rate_mismatch" },
    },
    {
      logId: "AUD-009",
      timestamp: fromMinutes(98),
      actorType: "merchant",
      actorId: DEMO_MERCHANT_ID,
      action: "gst_tx_flagged",
      entityId: "GST-0846",
      outcome: "pending",
      metadata: { reason: "hsn_uncertain" },
    },
    {
      logId: "AUD-010",
      timestamp: fromMinutes(74),
      actorType: "merchant",
      actorId: DEMO_MERCHANT_ID,
      action: "wallet_balance_checked",
      entityId: DEMO_MERCHANT_ID,
      amount: 47230,
      outcome: "success",
      metadata: { source: "wallet" },
    },
    {
      logId: "AUD-011",
      timestamp: fromMinutes(41),
      actorType: "system",
      actorId: "invoice-monitor",
      action: "offer_eligibility_computed",
      entityId: "INV-044",
      amount: 24225,
      outcome: "success",
      metadata: { scoreBand: "good", feeRate: 2.0 },
    },
    {
      logId: "AUD-012",
      timestamp: fromMinutes(12),
      actorType: "merchant",
      actorId: DEMO_MERCHANT_ID,
      action: "session_active",
      entityId: DEMO_MERCHANT_ID,
      outcome: "success",
      metadata: { lastScreen: "dashboard" },
    },
  ];
}

function createRameshRuntime(): MerchantRuntime {
  const transactions = buildGSTTransactions(847);
  const history = buildDailyRevenue(180);
  const trustHistory = buildTrustHistory(90);

  const profile: Merchant = {
    merchantId: DEMO_MERCHANT_ID,
    name: "Ramesh Kumar",
    gstin: "07AABCU9603R1ZP",
    businessName: "Ramesh General Store",
    category: "Grocery",
    phone: DEMO_PHONE,
    kycStatus: "verified",
    createdAt: new Date("2025-06-11").toISOString(),
    walletBalance: 47230,
  };

  const wallet: WalletBalance = {
    balance: 47230,
    currency: INR,
    lastUpdated: nowISO(),
  };

  const trustScore: TrustScore = {
    score: 74,
    bucket: "Good",
    components: {
      paymentRate: 24,
      consistency: 15,
      volumeTrend: 15,
      gstCompliance: 13,
      returnRate: 7,
    },
    history: trustHistory,
    lastUpdated: nowISO(),
  };

  const gstDraft: GSTDraft = {
    merchantId: DEMO_MERCHANT_ID,
    quarter: "Q1",
    year: 2026,
    transactions,
    summary: summarizeGST(transactions),
    generatedAt: nowISO(),
  };

  return {
    role: "merchant",
    profile,
    wallet,
    cashflowHistory: history,
    cashflowProjection: buildProjection(history),
    gstDraft,
    trustScore,
    invoices: buildRameshInvoices(),
    offers: [],
    notifications: buildRameshNotifications(),
    auditLog: buildRameshAuditEntries(),
    transfers: [],
    pinHash: PIN_HASH_1234,
  };
}

function createExtraMerchant(
  merchantId: string,
  name: string,
  businessName: string,
  category: string,
  walletBalance: number,
  trustScoreValue: number,
): MerchantRuntime {
  const base: MerchantRuntime = createRameshRuntime();
  base.profile = {
    ...base.profile,
    merchantId,
    name,
    businessName,
    category,
    walletBalance,
    phone: `+91-98${merchantId.slice(-8)}`,
    gstin: `07AA${merchantId.toUpperCase().slice(0, 10)}1ZP`,
  };
  base.wallet = {
    balance: walletBalance,
    currency: INR,
    lastUpdated: nowISO(),
  };
  base.trustScore = {
    ...base.trustScore,
    score: trustScoreValue,
    bucket: getTrustBucket(trustScoreValue),
    lastUpdated: nowISO(),
  };
  base.profile.walletBalance = walletBalance;
  base.auditLog = base.auditLog.slice(0, 6);
  base.notifications = base.notifications.slice(0, 2);
  base.pinHash = PIN_HASH_1234;

  return base;
}

function createAdminRuntime(): MerchantRuntime {
  const admin: MerchantRuntime = createRameshRuntime();
  admin.role = "admin";
  admin.profile = {
    merchantId: ADMIN_MERCHANT_ID,
    name: "ArthSetu Admin",
    gstin: "07AAECA2026A1ZA",
    businessName: "ArthSetu HQ",
    category: "Operations",
    phone: "+91-99999-00000",
    kycStatus: "verified",
    createdAt: new Date("2025-01-01").toISOString(),
    walletBalance: 0,
  };
  admin.wallet = {
    balance: 0,
    currency: INR,
    lastUpdated: nowISO(),
  };
  admin.pinHash = PIN_HASH_9999;
  admin.trustScore = {
    ...admin.trustScore,
    score: 86,
    bucket: "Excellent",
    lastUpdated: nowISO(),
  };
  admin.gstDraft = {
    ...admin.gstDraft,
    merchantId: ADMIN_MERCHANT_ID,
    transactions: [],
    summary: {
      totalTaxable: 0,
      totalCGST: 0,
      totalSGST: 0,
      netLiability: 0,
      flaggedCount: 0,
      totalCount: 0,
    },
  };
  admin.invoices = [];
  admin.offers = [];
  admin.notifications = [];
  admin.auditLog = [];

  return admin;
}

function createInitialState(): MockState {
  const ramesh = createRameshRuntime();

  return {
    merchants: {
      [DEMO_MERCHANT_ID]: ramesh,
      merchant_arya: createExtraMerchant("merchant_arya", "Arya Singh", "Arya Electronics", "Electronics", 86420, 67),
      merchant_neha: createExtraMerchant("merchant_neha", "Neha Bansal", "Neha Pharma", "Pharmacy", 65310, 79),
      merchant_rahul: createExtraMerchant("merchant_rahul", "Rahul Mehta", "Rahul Fashion Hub", "Clothing", 41180, 58),
      [ADMIN_MERCHANT_ID]: createAdminRuntime(),
    },
    whatsappLog: [],
    counters: {
      audit: 120,
      transfer: 810,
      offer: 140,
      filing: 32,
      notification: 220,
    },
  };
}

let state: MockState = createInitialState();

function getMerchantRuntime(merchantId: string): MerchantRuntime {
  const runtime = state.merchants[merchantId];
  if (!runtime) {
    throw new Error(`Merchant ${merchantId} not found`);
  }
  return runtime;
}

function pushAudit(
  merchantId: string,
  entry: Omit<AuditEntry, "logId" | "timestamp">,
): AuditEntry {
  state.counters.audit += 1;
  const log: AuditEntry = {
    logId: `AUD-${String(state.counters.audit).padStart(4, "0")}`,
    timestamp: nowISO(),
    ...entry,
  };

  const runtime = getMerchantRuntime(merchantId);
  runtime.auditLog.unshift(log);
  return log;
}

function pushNotification(
  merchantId: string,
  notif: Omit<Notification, "notifId" | "timestamp" | "read"> & { read?: boolean },
): Notification {
  state.counters.notification += 1;
  const next: Notification = {
    notifId: `NOTIF-${String(state.counters.notification).padStart(4, "0")}`,
    timestamp: nowISO(),
    read: notif.read ?? false,
    ...notif,
  };

  const runtime = getMerchantRuntime(merchantId);
  runtime.notifications.unshift(next);
  return next;
}

function createSessionFromMerchant(runtime: MerchantRuntime, role: UserSession["role"]): UserSession {
  const merchantId = runtime.profile.merchantId;
  return {
    userId: `user_${merchantId}`,
    name: runtime.profile.name,
    phone: runtime.profile.phone,
    role,
    merchantId: role === "merchant" ? merchantId : undefined,
    token: `mock-token-${merchantId}`,
    expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
  };
}

export const mockAdapter: AdapterInterface = {
  async getWalletBalance(merchantId) {
    return deepClone(getMerchantRuntime(merchantId).wallet);
  },

  async transfer(input) {
    const runtime = getMerchantRuntime(input.fromId);

    if (input.amount <= 0) {
      throw new Error("Transfer amount must be greater than zero");
    }
    if (input.amount > 100000) {
      throw new Error("Transfer exceeds mock daily limit");
    }
    if (runtime.wallet.balance < input.amount) {
      throw new Error("Insufficient wallet balance");
    }

    runtime.wallet.balance = round2(runtime.wallet.balance - input.amount);
    runtime.wallet.lastUpdated = nowISO();
    runtime.profile.walletBalance = runtime.wallet.balance;

    state.counters.transfer += 1;
    const audit = pushAudit(input.fromId, {
      actorType: "merchant",
      actorId: input.fromId,
      action: "transfer_initiated",
      entityId: input.toUpiId,
      amount: input.amount,
      outcome: "success",
      metadata: {
        toName: input.toName,
        note: input.note ?? "",
      },
    });

    const transfer: Transfer = {
      txId: `TRX-${String(state.counters.transfer).padStart(6, "0")}`,
      fromId: input.fromId,
      toUpiId: input.toUpiId,
      toName: input.toName,
      amount: input.amount,
      note: input.note ?? "",
      status: "success",
      timestamp: nowISO(),
      auditId: audit.logId,
    };

    runtime.transfers.unshift(transfer);

    pushNotification(input.fromId, {
      type: "transfer",
      title: "Transfer completed",
      body: `Rs. ${input.amount.toLocaleString("en-IN")} sent to ${input.toName}.`,
      actionUrl: "/merchant/transfers",
    });

    return deepClone(transfer);
  },

  async getCashflow(merchantId) {
    const runtime = getMerchantRuntime(merchantId);
    runtime.cashflowProjection = buildProjection(runtime.cashflowHistory);
    return deepClone({
      projection: runtime.cashflowProjection,
      history: runtime.cashflowHistory,
    });
  },

  async getGSTDraft(merchantId) {
    return deepClone(getMerchantRuntime(merchantId).gstDraft);
  },

  async updateGSTTransaction(merchantId, patch) {
    const runtime = getMerchantRuntime(merchantId);
    const row = runtime.gstDraft.transactions.find((tx) => tx.txId === patch.txId);

    if (!row) {
      throw new Error("Transaction not found");
    }

    if (patch.hsnCode) {
      row.hsnCode = patch.hsnCode;
    }
    if (typeof patch.gstRate === "number") {
      row.gstRate = patch.gstRate;
    }
    if (patch.category) {
      row.category = patch.category;
    }

    row.cgst = round2((row.amount * row.gstRate) / 2);
    row.sgst = round2((row.amount * row.gstRate) / 2);
    row.reviewFlag = false;
    row.editedByUser = true;

    runtime.gstDraft.summary = summarizeGST(runtime.gstDraft.transactions);

    pushAudit(merchantId, {
      actorType: "merchant",
      actorId: merchantId,
      action: "gst_transaction_updated",
      entityId: patch.txId,
      amount: row.amount,
      outcome: "success",
      metadata: {
        hsnCode: row.hsnCode,
        gstRate: row.gstRate,
      },
    });

    return deepClone(runtime.gstDraft);
  },

  async fileGST(merchantId) {
    const runtime = getMerchantRuntime(merchantId);

    runtime.gstDraft.transactions = runtime.gstDraft.transactions.map((tx) => ({
      ...tx,
      reviewFlag: false,
    }));
    runtime.gstDraft.summary = summarizeGST(runtime.gstDraft.transactions);
    runtime.gstDraft.generatedAt = nowISO();

    const oldScore = runtime.trustScore.score;
    runtime.trustScore.score = Math.max(runtime.trustScore.score, 78);
    runtime.trustScore.bucket = getTrustBucket(runtime.trustScore.score);
    runtime.trustScore.components.gstCompliance = Math.min(20, runtime.trustScore.components.gstCompliance + 4);
    runtime.trustScore.lastUpdated = nowISO();
    runtime.trustScore.history.push({
      date: new Date().toISOString().slice(0, 10),
      score: runtime.trustScore.score,
    });
    runtime.trustScore.history = runtime.trustScore.history.slice(-90);

    state.counters.filing += 1;
    const refId = `GST-REF-${new Date().getFullYear()}-${String(state.counters.filing).padStart(4, "0")}`;

    pushAudit(merchantId, {
      actorType: "merchant",
      actorId: merchantId,
      action: "gst_filed",
      entityId: refId,
      amount: runtime.gstDraft.summary.netLiability,
      outcome: "success",
      metadata: {
        quarter: `${runtime.gstDraft.quarter} ${runtime.gstDraft.year}`,
        scoreBefore: oldScore,
        scoreAfter: runtime.trustScore.score,
      },
    });

    pushNotification(merchantId, {
      type: "gst",
      title: "GST filing successful",
      body: `Filed ${runtime.gstDraft.quarter} ${runtime.gstDraft.year}. Reference ${refId}.`,
      actionUrl: "/merchant/gst/history",
    });

    state.whatsappLog.push({
      phone: runtime.profile.phone,
      message: `GST filed successfully. Reference ${refId}`,
      timestamp: nowISO(),
    });

    return {
      status: "success",
      refId,
      filedAt: nowISO(),
      whatsappSent: true,
      phone: runtime.profile.phone,
    };
  },

  async getTrustScore(merchantId) {
    return deepClone(getMerchantRuntime(merchantId).trustScore);
  },

  async getInvoices(merchantId) {
    return deepClone(getMerchantRuntime(merchantId).invoices);
  },

  async requestCreditOffer(merchantId, invoiceId) {
    const runtime = getMerchantRuntime(merchantId);
    const invoice = runtime.invoices.find((row) => row.invoiceId === invoiceId);
    if (!invoice) {
      throw new Error("Invoice not found");
    }

    if (invoice.status !== "OVERDUE") {
      throw new Error("Only overdue invoices are eligible for offers");
    }

    const existing = runtime.offers.find((offer) => offer.invoiceId === invoiceId && offer.status === "pending_acceptance");
    if (existing) {
      return deepClone(existing);
    }

    state.counters.offer += 1;
    const offer: CreditOffer = {
      offerId: `OFF-${String(state.counters.offer).padStart(5, "0")}`,
      invoiceId,
      advanceAmount: 24225,
      feeRate: 2,
      repaymentTrigger: `Auto-repay when ${invoice.buyerName} settles invoice`,
      status: "pending_acceptance",
      generatedAt: nowISO(),
    };

    runtime.offers.unshift(offer);

    pushAudit(merchantId, {
      actorType: "system",
      actorId: "finance-engine",
      action: "credit_offer_generated",
      entityId: offer.offerId,
      amount: offer.advanceAmount,
      outcome: "success",
      metadata: {
        invoiceId,
        feeRate: offer.feeRate,
      },
    });

    return deepClone(offer);
  },

  async acceptCreditOffer(merchantId, offerId) {
    const runtime = getMerchantRuntime(merchantId);
    const offer = runtime.offers.find((row) => row.offerId === offerId);

    if (!offer) {
      throw new Error("Offer not found");
    }
    if (offer.status !== "pending_acceptance") {
      throw new Error("Offer is not available for acceptance");
    }

    offer.status = "accepted";
    const invoice = runtime.invoices.find((row) => row.invoiceId === offer.invoiceId);
    if (invoice) {
      invoice.status = "FINANCED";
      invoice.advanceAmount = offer.advanceAmount;
      invoice.feeRate = offer.feeRate;
      invoice.repaid = false;
      invoice.overdueDays = 0;
    }

    runtime.wallet.balance = round2(runtime.wallet.balance + offer.advanceAmount);
    runtime.wallet.lastUpdated = nowISO();
    runtime.profile.walletBalance = runtime.wallet.balance;

    pushAudit(merchantId, {
      actorType: "merchant",
      actorId: merchantId,
      action: "credit_offer_accepted",
      entityId: offerId,
      amount: offer.advanceAmount,
      outcome: "success",
      metadata: {
        invoiceId: offer.invoiceId,
        feeRate: offer.feeRate,
      },
    });

    pushNotification(merchantId, {
      type: "finance",
      title: "Advance approved",
      body: `Rs. ${offer.advanceAmount.toLocaleString("en-IN")} will be disbursed within 4 hours.`,
      actionUrl: "/merchant/wallet",
    });

    state.whatsappLog.push({
      phone: runtime.profile.phone,
      message: `Advance of Rs. ${offer.advanceAmount.toLocaleString("en-IN")} approved for ${offer.invoiceId}`,
      timestamp: nowISO(),
    });

    return deepClone(offer);
  },

  async getNotifications(merchantId) {
    return deepClone(getMerchantRuntime(merchantId).notifications);
  },

  async getAuditLog(merchantId) {
    return deepClone(getMerchantRuntime(merchantId).auditLog);
  },

  async getMerchantProfile(merchantId) {
    return deepClone(getMerchantRuntime(merchantId).profile);
  },

  async resetDemo() {
    state = createInitialState();
    const runtime = getMerchantRuntime(DEMO_MERCHANT_ID);

    pushAudit(DEMO_MERCHANT_ID, {
      actorType: "system",
      actorId: "demo-reset",
      action: "demo_reset",
      entityId: DEMO_MERCHANT_ID,
      outcome: "success",
      metadata: {
        restored: true,
      },
    });

    pushNotification(DEMO_MERCHANT_ID, {
      type: "alert",
      title: "Demo reset complete",
      body: "Ramesh profile restored with seeded GST and invoice data.",
      actionUrl: "/merchant/dashboard",
    });

    return createSessionFromMerchant(runtime, "merchant");
  },

  async sendWhatsappAlert(input: SendWhatsappAlertInput) {
    const runtime = getMerchantRuntime(input.merchantId);
    state.whatsappLog.push({
      phone: input.phone,
      message: input.message,
      timestamp: nowISO(),
    });

    pushAudit(input.merchantId, {
      actorType: "system",
      actorId: "whatsapp-service",
      action: "whatsapp_alert_sent",
      entityId: runtime.profile.merchantId,
      outcome: "success",
      metadata: {
        phone: input.phone,
        messagePreview: input.message.slice(0, 80),
      },
    });

    return {
      sent: true,
      queuedAt: nowISO(),
    };
  },

  async getMerchants() {
    return deepClone(
      Object.values(state.merchants)
        .filter((runtime) => runtime.profile.merchantId !== ADMIN_MERCHANT_ID)
        .map((runtime) => runtime.profile),
    );
  },

  async loginWithPin(merchantId, pinHash) {
    const normalized = merchantId.trim().toLowerCase();
    const mapped = normalized === "admin_arth" ? ADMIN_MERCHANT_ID : normalized;
    const runtime = getMerchantRuntime(mapped);

    if (runtime.pinHash !== pinHash) {
      throw new Error("Invalid Merchant ID or PIN");
    }

    const role: UserSession["role"] = runtime.role === "admin" ? "admin" : runtime.role === "consumer" ? "consumer" : "merchant";

    const session = createSessionFromMerchant(runtime, role);

    pushAudit(mapped, {
      actorType: role === "admin" ? "admin" : "merchant",
      actorId: mapped,
      action: "login_success",
      entityId: mapped,
      outcome: "success",
      metadata: {
        role,
      },
    });

    return {
      session,
      merchant: role === "merchant" ? deepClone(runtime.profile) : undefined,
    } satisfies AuthResult;
  },

  async registerAccount(input: RegisterAccountInput) {
    const now = nowISO();
    const rawId =
      input.merchantId ||
      (input.role === "merchant" ? input.businessName || input.name : `${input.role}_${Math.random().toString(36).slice(2, 8)}`);

    const merchantId =
      rawId
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9_]/g, "_")
        .replace(/_+/g, "_")
        .replace(/^_|_$/g, "") || `merchant_${Math.random().toString(36).slice(2, 8)}`;

    if (state.merchants[merchantId]) {
      throw new Error("Merchant ID already exists");
    }

    const runtime = createRameshRuntime();
    runtime.role = input.role;
    runtime.pinHash = input.pinHash;
    runtime.profile = {
      ...runtime.profile,
      merchantId,
      name: input.name,
      businessName: input.businessName || input.name,
      category: input.category || "General",
      phone: input.phone,
      gstin: input.gstin || "",
      kycStatus: "pending",
      createdAt: now,
      walletBalance: 0,
    };

    runtime.wallet = {
      balance: 0,
      currency: INR,
      lastUpdated: now,
    };
    runtime.cashflowHistory = [];
    runtime.cashflowProjection = {
      p30: { amount: 0, confidence: 90 },
      p60: { amount: 0, confidence: 82 },
      p90: { amount: 0, confidence: 75 },
      generatedAt: now,
    };
    runtime.gstDraft = {
      merchantId,
      quarter: "Q1",
      year: new Date().getFullYear(),
      transactions: [],
      summary: {
        totalTaxable: 0,
        totalCGST: 0,
        totalSGST: 0,
        netLiability: 0,
        flaggedCount: 0,
        totalCount: 0,
      },
      generatedAt: now,
    };
    runtime.trustScore = {
      score: input.role === "merchant" ? 50 : 0,
      bucket: input.role === "merchant" ? "Medium" : "Low",
      components: {
        paymentRate: 0,
        consistency: 0,
        volumeTrend: 0,
        gstCompliance: 0,
        returnRate: 0,
      },
      history: [],
      lastUpdated: now,
    };
    runtime.invoices = [];
    runtime.offers = [];
    runtime.notifications = [];
    runtime.auditLog = [];
    runtime.transfers = [];

    state.merchants[merchantId] = runtime;

    pushAudit(merchantId, {
      actorType: input.role === "admin" ? "admin" : "merchant",
      actorId: merchantId,
      action: "account_registered",
      entityId: merchantId,
      outcome: "success",
      metadata: {
        role: input.role,
      },
    });

    if (input.role === "merchant") {
      pushNotification(merchantId, {
        type: "alert",
        title: "Welcome to ArthSetu",
        body: "Your merchant workspace is ready.",
        actionUrl: "/merchant/dashboard",
      });
    }

    const role: UserSession["role"] = input.role;
    const session = createSessionFromMerchant(runtime, role);
    return {
      session,
      merchant: role === "merchant" ? deepClone(runtime.profile) : undefined,
    } satisfies AuthResult;
  },

  async markNotificationRead(merchantId, notifId) {
    const runtime = getMerchantRuntime(merchantId);
    const notif = runtime.notifications.find((row) => row.notifId === notifId);
    if (notif) {
      notif.read = true;
    }
  },

  async markAllNotificationsRead(merchantId) {
    const runtime = getMerchantRuntime(merchantId);
    runtime.notifications = runtime.notifications.map((row) => ({ ...row, read: true }));
  },
};

export function getMockAdapter(): AdapterInterface {
  return mockAdapter;
}
