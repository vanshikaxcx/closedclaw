import type {
  AppNotification,
  AuditEvent,
  AuthSession,
  CashflowPayload,
  CreditOfferPayload,
  DataAdapter,
  GstDraftPayload,
  GstTransactionRow,
  InvoiceRecord,
  MerchantOverview,
  MerchantSummary,
  TransferResult,
  TrustScorePayload,
  WalletPayload,
} from "@/lib/adapters/types";

interface MerchantStore {
  sessionTemplate: Omit<AuthSession, "isDemo">;
  pin: string;
  trustScore: TrustScorePayload;
  gstDraft: GstDraftPayload;
  invoices: InvoiceRecord[];
  cashflow: Record<30 | 60 | 90, CashflowPayload>;
  walletBalance: number;
  notifications: AppNotification[];
  auditLog: AuditEvent[];
}

interface MockDb {
  merchants: Record<string, MerchantStore>;
  activeOffers: Record<string, CreditOfferPayload>;
}

const demoSeed = createSeedDb();
let db: MockDb = structuredClone(demoSeed);

function nowIso(): string {
  return new Date().toISOString();
}

function wait(ms = 220): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function hashId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

function bucketFromScore(score: number): TrustScorePayload["bucket"] {
  if (score < 45) {
    return "Poor";
  }
  if (score < 65) {
    return "Fair";
  }
  if (score < 82) {
    return "Good";
  }
  return "Excellent";
}

function recalcScore(merchant: MerchantStore, delta: number): void {
  merchant.trustScore.score = Math.max(35, Math.min(92, merchant.trustScore.score + delta));
  merchant.trustScore.bucket = bucketFromScore(merchant.trustScore.score);
  merchant.trustScore.history = [
    {
      date: new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short" }),
      score: merchant.trustScore.score,
    },
    ...merchant.trustScore.history,
  ].slice(0, 6);
}

function addAudit(merchant: MerchantStore, event: Omit<AuditEvent, "id" | "timestamp">): void {
  merchant.auditLog = [
    {
      id: hashId("audit"),
      timestamp: nowIso(),
      ...event,
    },
    ...merchant.auditLog,
  ];
}

function addNotification(merchant: MerchantStore, title: string, body: string): void {
  merchant.notifications = [
    {
      id: hashId("notif"),
      title,
      body,
      createdAt: nowIso(),
      read: false,
    },
    ...merchant.notifications,
  ];
}

function findMerchant(merchantId: string): MerchantStore {
  const merchant = db.merchants[merchantId];
  if (!merchant) {
    throw new Error("Merchant not found");
  }
  return merchant;
}

function createSeedDb(): MockDb {
  const trustScore: TrustScorePayload = {
    score: 78,
    bucket: "Good",
    components: {
      paymentRate: 24.0,
      consistency: 15.8,
      volumeTrend: 15.9,
      gstCompliance: 14.2,
      returnRate: 8.1,
    },
    history: [
      { date: "03 Apr", score: 78 },
      { date: "01 Apr", score: 76 },
      { date: "28 Mar", score: 74 },
      { date: "25 Mar", score: 73 },
    ],
  };

  const gstRows: GstTransactionRow[] = [
    {
      txId: "TXN-90031",
      description: "PayBot POS - Grocery batch",
      amount: 18450,
      gstRate: 0.18,
      hsnCode: "21069099",
      gstCategory: "Sales",
      status: "FLAGGED",
    },
    {
      txId: "TXN-90032",
      description: "PayBot QR - Dairy wholesale",
      amount: 9050,
      gstRate: 0.12,
      hsnCode: "04029910",
      gstCategory: "Sales",
      status: "FLAGGED",
    },
    {
      txId: "TXN-90033",
      description: "Inventory procurement",
      amount: 6640,
      gstRate: 0.18,
      hsnCode: "30049011",
      gstCategory: "Purchase",
      status: "AUTO_CLASSIFIED",
    },
    {
      txId: "TXN-90034",
      description: "Packaging material",
      amount: 3120,
      gstRate: 0.18,
      hsnCode: "39239090",
      gstCategory: "Expense",
      status: "CONFIRMED",
    },
  ];

  const gstDraft: GstDraftPayload = {
    period: "Mar-2026",
    totalCount: gstRows.length,
    flaggedCount: gstRows.filter((row) => row.status === "FLAGGED").length,
    rows: gstRows,
    summary: {
      taxableValue: 37260,
      gstLiability: 5650,
      netTaxLiability: 4720,
    },
  };

  const invoices: InvoiceRecord[] = [
    {
      invoiceId: "INV-12084",
      buyerName: "Sharma Retail Mart",
      amount: 92000,
      dueDate: "2026-03-14",
      overdueDays: 20,
      status: "OVERDUE",
    },
    {
      invoiceId: "INV-12093",
      buyerName: "K2 Supplies",
      amount: 51000,
      dueDate: "2026-03-30",
      overdueDays: 4,
      status: "PENDING",
    },
    {
      invoiceId: "INV-12104",
      buyerName: "UrbanBasket Hub",
      amount: 128000,
      dueDate: "2026-03-18",
      overdueDays: 16,
      status: "OVERDUE",
    },
  ];

  const cashflowFactory = (windowDays: 30 | 60 | 90): CashflowPayload => {
    const points = Array.from({ length: Math.min(12, Math.floor(windowDays / 5)) }).map((_, index) => {
      const inflow = 42000 + index * 1800;
      const outflow = 27000 + index * 900;
      return {
        date: `${index * 5 + 1}d`,
        inflow,
        outflow,
        net: inflow - outflow,
      };
    });

    return {
      windowDays,
      points,
      totals: {
        inflow: points.reduce((sum, point) => sum + point.inflow, 0),
        outflow: points.reduce((sum, point) => sum + point.outflow, 0),
        net: points.reduce((sum, point) => sum + point.net, 0),
      },
    };
  };

  const merchant: MerchantStore = {
    sessionTemplate: {
      userId: "u_seller_a",
      merchantId: "seller_a",
      merchantName: "Ramesh Kirana Store",
      role: "merchant",
      phone: "+919876543210",
      email: "ramesh@arthsetu.demo",
    },
    pin: "1234",
    trustScore,
    gstDraft,
    invoices,
    cashflow: {
      30: cashflowFactory(30),
      60: cashflowFactory(60),
      90: cashflowFactory(90),
    },
    walletBalance: 286400,
    notifications: [
      {
        id: "notif_seed_1",
        title: "GST review pending",
        body: "2 transactions need classification before filing.",
        createdAt: nowIso(),
        read: false,
      },
    ],
    auditLog: [
      {
        id: "audit_seed_1",
        type: "demo_bootstrap",
        message: "Demo dataset initialized for merchant workflow.",
        timestamp: nowIso(),
        severity: "info",
      },
    ],
  };

  const admin: MerchantStore = {
    sessionTemplate: {
      userId: "u_admin_1",
      merchantId: "admin_hq",
      merchantName: "ArthSetu Operations",
      role: "admin",
      phone: "+919999990000",
      email: "admin@arthsetu.demo",
    },
    pin: "9999",
    trustScore: {
      score: 84,
      bucket: "Excellent",
      components: {
        paymentRate: 25,
        consistency: 16,
        volumeTrend: 16,
        gstCompliance: 16,
        returnRate: 11,
      },
      history: [
        { date: "03 Apr", score: 84 },
        { date: "01 Apr", score: 83 },
      ],
    },
    gstDraft: {
      period: "Mar-2026",
      totalCount: 0,
      flaggedCount: 0,
      rows: [],
      summary: {
        taxableValue: 0,
        gstLiability: 0,
        netTaxLiability: 0,
      },
    },
    invoices: [],
    cashflow: {
      30: cashflowFactory(30),
      60: cashflowFactory(60),
      90: cashflowFactory(90),
    },
    walletBalance: 0,
    notifications: [],
    auditLog: [],
  };

  return {
    merchants: {
      seller_a: merchant,
      admin_hq: admin,
    },
    activeOffers: {},
  };
}

const mockAdapter: DataAdapter = {
  mode: "mock",

  async login(merchantId: string, pin: string): Promise<AuthSession> {
    await wait();

    const normalized = merchantId.trim().toLowerCase();
    const mappedId = normalized === "admin_arth" ? "admin_hq" : normalized;
    const merchant = db.merchants[mappedId];

    if (!merchant || merchant.pin !== pin) {
      throw new Error("Invalid Merchant ID or PIN");
    }

    return {
      ...merchant.sessionTemplate,
      isDemo: false,
    };
  },

  async resetDemo(): Promise<AuthSession> {
    await wait(260);
    db = structuredClone(demoSeed);

    const merchant = findMerchant("seller_a");
    addAudit(merchant, {
      type: "demo_reset",
      message: "Demo mode reset completed with fresh GST + invoice scenario.",
      severity: "info",
    });

    addNotification(
      merchant,
      "Demo mode ready",
      "You are signed in as Ramesh with seeded judging data.",
    );

    return {
      ...merchant.sessionTemplate,
      isDemo: true,
    };
  },

  async getTrustScore(merchantId: string): Promise<TrustScorePayload> {
    await wait(150);
    return structuredClone(findMerchant(merchantId).trustScore);
  },

  async getGstDraft(merchantId: string): Promise<GstDraftPayload> {
    await wait(140);
    return structuredClone(findMerchant(merchantId).gstDraft);
  },

  async updateGstTransaction(
    merchantId: string,
    txId: string,
    patch: Partial<Pick<GstTransactionRow, "gstRate" | "hsnCode" | "gstCategory">>,
  ): Promise<GstDraftPayload> {
    await wait(160);

    const merchant = findMerchant(merchantId);
    const row = merchant.gstDraft.rows.find((candidate) => candidate.txId === txId);

    if (!row) {
      throw new Error("GST transaction not found");
    }

    if (typeof patch.gstRate === "number") {
      row.gstRate = patch.gstRate;
    }
    if (typeof patch.hsnCode === "string") {
      row.hsnCode = patch.hsnCode;
    }
    if (typeof patch.gstCategory === "string") {
      row.gstCategory = patch.gstCategory;
    }

    row.status = "AUTO_CLASSIFIED";
    merchant.gstDraft.flaggedCount = merchant.gstDraft.rows.filter((candidate) => candidate.status === "FLAGGED").length;

    addAudit(merchant, {
      type: "gst_row_update",
      message: `GST row ${txId} reclassified and saved.`,
      severity: "info",
    });

    return structuredClone(merchant.gstDraft);
  },

  async fileGstReturn(merchantId: string): Promise<{ filingId: string; whatsappSentTo: string }> {
    await wait(260);

    const merchant = findMerchant(merchantId);
    merchant.gstDraft.rows = merchant.gstDraft.rows.map((row) => ({
      ...row,
      status: row.status === "FLAGGED" ? "CONFIRMED" : row.status,
    }));
    merchant.gstDraft.flaggedCount = 0;
    merchant.gstDraft.lastFiledAt = nowIso();

    recalcScore(merchant, 3);

    addAudit(merchant, {
      type: "gst_filed",
      message: "GST return filed successfully and TrustScore updated.",
      severity: "success",
    });

    addNotification(
      merchant,
      "GST filed",
      "Return filed for current period and WhatsApp confirmation dispatched.",
    );

    return {
      filingId: hashId("gst"),
      whatsappSentTo: merchant.sessionTemplate.phone,
    };
  },

  async getInvoices(merchantId: string): Promise<InvoiceRecord[]> {
    await wait(140);
    return structuredClone(findMerchant(merchantId).invoices);
  },

  async requestCreditOffer(merchantId: string, invoiceId: string): Promise<CreditOfferPayload> {
    await wait(180);

    const merchant = findMerchant(merchantId);
    const invoice = merchant.invoices.find((candidate) => candidate.invoiceId === invoiceId);

    if (!invoice) {
      throw new Error("Invoice not found");
    }

    if (invoice.status !== "OVERDUE") {
      return {
        offerId: hashId("offer"),
        invoiceId,
        advanceAmount: 0,
        feeRate: 0,
        status: "declined",
        reason: "Only overdue invoices are currently eligible for financing",
      };
    }

    const offer: CreditOfferPayload = {
      offerId: hashId("offer"),
      invoiceId,
      advanceAmount: Math.round(invoice.amount * 0.82),
      feeRate: 2.1,
      status: "pending_acceptance",
    };

    db.activeOffers[offer.offerId] = offer;

    addAudit(merchant, {
      type: "offer_generated",
      message: `Credit offer generated for ${invoiceId}.`,
      severity: "info",
    });

    return structuredClone(offer);
  },

  async acceptCreditOffer(
    merchantId: string,
    offerId: string,
  ): Promise<{ disbursalId: string; whatsappSentTo: string }> {
    await wait(220);

    const merchant = findMerchant(merchantId);
    const offer = db.activeOffers[offerId];

    if (!offer || offer.status !== "pending_acceptance") {
      throw new Error("Offer is unavailable or already processed");
    }

    offer.status = "accepted";

    merchant.invoices = merchant.invoices.map((invoice) =>
      invoice.invoiceId === offer.invoiceId
        ? {
            ...invoice,
            status: "FINANCED",
          }
        : invoice,
    );

    merchant.walletBalance += offer.advanceAmount;
    recalcScore(merchant, 2);

    addAudit(merchant, {
      type: "credit_accepted",
      message: `Invoice ${offer.invoiceId} financed and disbursed successfully.`,
      severity: "success",
    });

    addNotification(
      merchant,
      "Advance disbursed",
      `Invoice ${offer.invoiceId} offer accepted. Wallet updated instantly.`,
    );

    return {
      disbursalId: hashId("disbursal"),
      whatsappSentTo: merchant.sessionTemplate.phone,
    };
  },

  async applyRepayment(merchantId: string, invoiceId: string): Promise<{ repaymentId: string }> {
    await wait(180);

    const merchant = findMerchant(merchantId);
    const invoice = merchant.invoices.find((candidate) => candidate.invoiceId === invoiceId);

    if (!invoice) {
      throw new Error("Invoice not found");
    }

    invoice.status = "CLOSED";
    invoice.overdueDays = 0;

    addAudit(merchant, {
      type: "repayment_closed",
      message: `Buyer repayment received for ${invoiceId}. Invoice closed.`,
      severity: "success",
    });

    return {
      repaymentId: hashId("repay"),
    };
  },

  async getCashflow(merchantId: string, windowDays: 30 | 60 | 90): Promise<CashflowPayload> {
    await wait(120);
    return structuredClone(findMerchant(merchantId).cashflow[windowDays]);
  },

  async getWallet(merchantId: string): Promise<WalletPayload> {
    await wait(120);
    const merchant = findMerchant(merchantId);
    return {
      balance: merchant.walletBalance,
      lastUpdatedAt: nowIso(),
    };
  },

  async transferFunds(merchantId: string, to: string, amount: number): Promise<TransferResult> {
    await wait(220);

    const merchant = findMerchant(merchantId);

    if (amount <= 0) {
      return {
        transferId: hashId("transfer"),
        to,
        amount,
        status: "failed",
        reason: "Transfer amount should be positive",
      };
    }

    if (merchant.walletBalance < amount) {
      return {
        transferId: hashId("transfer"),
        to,
        amount,
        status: "failed",
        reason: "Insufficient wallet balance",
      };
    }

    merchant.walletBalance -= amount;

    addAudit(merchant, {
      type: "wallet_transfer",
      message: `Transfer of Rs. ${amount.toLocaleString("en-IN")} sent to ${to}.`,
      severity: "info",
    });

    return {
      transferId: hashId("transfer"),
      to,
      amount,
      status: "success",
    };
  },

  async getAuditLog(merchantId: string): Promise<AuditEvent[]> {
    await wait(120);
    return structuredClone(findMerchant(merchantId).auditLog);
  },

  async getNotifications(merchantId: string): Promise<AppNotification[]> {
    await wait(100);
    return structuredClone(findMerchant(merchantId).notifications);
  },

  async getMerchants(): Promise<MerchantSummary[]> {
    await wait(180);

    return Object.values(db.merchants)
      .filter((merchant) => merchant.sessionTemplate.role === "merchant")
      .map((merchant) => ({
        merchantId: merchant.sessionTemplate.merchantId,
        merchantName: merchant.sessionTemplate.merchantName,
        trustScore: merchant.trustScore.score,
        gstFlaggedCount: merchant.gstDraft.flaggedCount,
        overdueInvoices: merchant.invoices.filter((invoice) => invoice.status === "OVERDUE").length,
        walletBalance: merchant.walletBalance,
      }));
  },

  async getMerchantOverview(merchantId: string): Promise<MerchantOverview> {
    await wait(160);
    const merchant = findMerchant(merchantId);

    return {
      merchantId: merchant.sessionTemplate.merchantId,
      merchantName: merchant.sessionTemplate.merchantName,
      trustScore: merchant.trustScore.score,
      gstFlaggedCount: merchant.gstDraft.flaggedCount,
      overdueInvoices: merchant.invoices.filter((invoice) => invoice.status === "OVERDUE").length,
      walletBalance: merchant.walletBalance,
      phone: merchant.sessionTemplate.phone,
      totalInvoices: merchant.invoices.length,
      gstPeriod: merchant.gstDraft.period,
    };
  },
};

export function resetMockData(): void {
  db = structuredClone(demoSeed);
}

export function getMockAdapter(): DataAdapter {
  return mockAdapter;
}
