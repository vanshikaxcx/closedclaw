export type UserRole = "merchant" | "admin";
export type AdapterMode = "mock" | "live";

export interface AuthSession {
  userId: string;
  merchantId: string;
  merchantName: string;
  role: UserRole;
  phone: string;
  email?: string;
  isDemo: boolean;
}

export interface TrustScorePoint {
  date: string;
  score: number;
}

export interface TrustScorePayload {
  score: number;
  bucket: "Poor" | "Fair" | "Good" | "Excellent";
  components: {
    paymentRate: number;
    consistency: number;
    volumeTrend: number;
    gstCompliance: number;
    returnRate: number;
  };
  history: TrustScorePoint[];
}

export type GstTransactionStatus = "FLAGGED" | "AUTO_CLASSIFIED" | "CONFIRMED";

export interface GstTransactionRow {
  txId: string;
  description: string;
  amount: number;
  gstRate: number;
  hsnCode: string;
  gstCategory: string;
  status: GstTransactionStatus;
}

export interface GstDraftPayload {
  period: string;
  totalCount: number;
  flaggedCount: number;
  rows: GstTransactionRow[];
  summary: {
    taxableValue: number;
    gstLiability: number;
    netTaxLiability: number;
  };
  lastFiledAt?: string;
}

export type InvoiceStatus = "PENDING" | "OVERDUE" | "FINANCED" | "PAID" | "CLOSED";

export interface InvoiceRecord {
  invoiceId: string;
  buyerName: string;
  amount: number;
  dueDate: string;
  overdueDays: number;
  status: InvoiceStatus;
}

export interface CreditOfferPayload {
  offerId: string;
  invoiceId: string;
  advanceAmount: number;
  feeRate: number;
  status: "pending_acceptance" | "accepted" | "declined";
  reason?: string;
}

export interface CashflowPoint {
  date: string;
  inflow: number;
  outflow: number;
  net: number;
}

export interface CashflowPayload {
  windowDays: 30 | 60 | 90;
  points: CashflowPoint[];
  totals: {
    inflow: number;
    outflow: number;
    net: number;
  };
}

export interface WalletPayload {
  balance: number;
  lastUpdatedAt: string;
}

export interface TransferResult {
  transferId: string;
  to: string;
  amount: number;
  status: "success" | "failed";
  reason?: string;
}

export interface AuditEvent {
  id: string;
  type: string;
  message: string;
  timestamp: string;
  severity: "info" | "success" | "warning" | "error";
}

export interface AppNotification {
  id: string;
  title: string;
  body: string;
  createdAt: string;
  read: boolean;
}

export interface MerchantSummary {
  merchantId: string;
  merchantName: string;
  trustScore: number;
  gstFlaggedCount: number;
  overdueInvoices: number;
  walletBalance: number;
}

export interface MerchantOverview extends MerchantSummary {
  phone: string;
  totalInvoices: number;
  gstPeriod: string;
}

export interface DataAdapter {
  mode: AdapterMode;
  login(merchantId: string, pin: string): Promise<AuthSession>;
  resetDemo(): Promise<AuthSession>;
  getTrustScore(merchantId: string): Promise<TrustScorePayload>;
  getGstDraft(merchantId: string): Promise<GstDraftPayload>;
  updateGstTransaction(
    merchantId: string,
    txId: string,
    patch: Partial<Pick<GstTransactionRow, "gstRate" | "hsnCode" | "gstCategory">>,
  ): Promise<GstDraftPayload>;
  fileGstReturn(merchantId: string): Promise<{ filingId: string; whatsappSentTo: string }>;
  getInvoices(merchantId: string): Promise<InvoiceRecord[]>;
  requestCreditOffer(merchantId: string, invoiceId: string): Promise<CreditOfferPayload>;
  acceptCreditOffer(
    merchantId: string,
    offerId: string,
  ): Promise<{ disbursalId: string; whatsappSentTo: string }>;
  applyRepayment(merchantId: string, invoiceId: string): Promise<{ repaymentId: string }>;
  getCashflow(merchantId: string, windowDays: 30 | 60 | 90): Promise<CashflowPayload>;
  getWallet(merchantId: string): Promise<WalletPayload>;
  transferFunds(merchantId: string, to: string, amount: number): Promise<TransferResult>;
  getAuditLog(merchantId: string): Promise<AuditEvent[]>;
  getNotifications(merchantId: string): Promise<AppNotification[]>;
  getMerchants(): Promise<MerchantSummary[]>;
  getMerchantOverview(merchantId: string): Promise<MerchantOverview>;
}
