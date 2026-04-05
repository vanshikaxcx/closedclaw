export type KYCStatus = "pending" | "verified" | "rejected";
export type UserRole = "consumer" | "merchant" | "admin";

export interface Merchant {
  merchantId: string;
  name: string;
  gstin: string;
  businessName: string;
  category: string;
  phone: string;
  kycStatus: KYCStatus;
  createdAt: string;
  walletBalance: number;
}

export interface UserSession {
  userId: string;
  name: string;
  phone: string;
  role: UserRole;
  merchantId?: string;
  token: string;
  expiresAt: string;
}

export interface WalletBalance {
  balance: number;
  currency: string;
  lastUpdated: string;
}

export type TransferStatus = "success" | "failed" | "pending";

export interface Transfer {
  txId: string;
  fromId: string;
  toUpiId: string;
  toName: string;
  amount: number;
  note: string;
  status: TransferStatus;
  timestamp: string;
  auditId: string;
}

export interface ProjectionPoint {
  amount: number;
  confidence: number;
}

export interface CashflowProjection {
  p30: ProjectionPoint;
  p60: ProjectionPoint;
  p90: ProjectionPoint;
  generatedAt: string;
}

export interface DailyRevenue {
  date: string;
  amount: number;
  transactionCount: number;
  isProjected: boolean;
  lowerBound: number;
  upperBound: number;
}

export type GSTCategory = "B2B" | "B2C_LOCAL" | "B2C_INTERSTATE" | "EXEMPT";

export interface GSTTransaction {
  txId: string;
  description: string;
  amount: number;
  hsnCode: string;
  gstRate: number;
  cgst: number;
  sgst: number;
  category: GSTCategory;
  reviewFlag: boolean;
  editedByUser: boolean;
}

export interface GSTDraft {
  merchantId: string;
  quarter: string;
  year: number;
  transactions: GSTTransaction[];
  summary: {
    totalTaxable: number;
    totalCGST: number;
    totalSGST: number;
    netLiability: number;
    flaggedCount: number;
    totalCount: number;
  };
  generatedAt: string;
}

export type GSTReviewStatus = "needs_review" | "ready";

export interface GSTServiceTransaction {
  txId: string;
  description: string;
  amount: number;
  hsnCode: string;
  gstRate: number;
  gstCategory: GSTCategory;
  cgst: number;
  sgst: number;
  reviewFlag: boolean;
  status: GSTReviewStatus;
}

export interface GSTDashboard {
  merchantId: string;
  summary: {
    totalTransactions: number;
    flaggedTransactions: number;
    totalTaxable: number;
    totalCGST: number;
    totalSGST: number;
    netLiability: number;
    lastGeneratedAt: string;
  };
  gstr1Generated: boolean;
  gstr3bGenerated: boolean;
}

export interface GSTReviewQueueItem {
  queueId: string;
  merchantId: string;
  txId: string;
  description: string;
  amount: number;
  currentHSN: string;
  currentGSTRate: number;
  gstCategory: GSTCategory;
  reviewFlag: boolean;
  status: GSTReviewStatus;
}

export interface ResolveReviewItemPayload {
  hsnCode?: string;
  gstRate?: number;
  status?: "resolved" | "updated";
}

export interface ResolveReviewItemResult {
  status: "updated" | "resolved" | "success";
  queueId: string;
  merchantId: string;
  txId: string;
  updatedAt: string;
}

export interface GSTR1TableRow {
  txId: string;
  description: string;
  amount: number;
  hsnCode: string;
  gstRate: number;
  cgst: number;
  sgst: number;
}

export interface GSTR1Draft {
  merchantId: string;
  generatedAt: string;
  table4: GSTR1TableRow[];
  table5: GSTR1TableRow[];
  table7: GSTR1TableRow[];
  summary: {
    totalRecords: number;
    totalTaxableValue: number;
    totalTax: number;
    b2bRecords: number;
    b2cRecords: number;
    exemptRecords: number;
  };
}

export interface GSTR1GenerationResult {
  status: "completed" | "started";
  merchantId: string;
  generatedAt: string;
  recordCount: number;
}

export interface GSTR3BSummary {
  merchantId: string;
  generatedAt: string;
  taxableValue: number;
  exemptValue: number;
  totalCGST: number;
  totalSGST: number;
  itcAvailable: number;
  netPayable: number;
  recordCount: number;
}

export interface GSTR3BGenerationResult {
  status: "completed" | "started";
  merchantId: string;
  generatedAt: string;
  recordCount: number;
}

export interface OCRItem {
  description: string;
  quantity?: number | null;
  amount: number;
}

export interface OCRStructuredResult {
  vendorName: string;
  vendorGstin: string;
  items: OCRItem[];
  grandTotal: number;
}

export interface OCRSaveResult {
  status: "success";
  saved: boolean;
  savedAt: string;
}

export interface GSTVoiceAudioResult {
  transcription: string;
  responseText: string;
  audioBase64: string | null;
}

export interface GSTVoiceTextResult {
  responseText: string;
}

export interface GSTFilingResult {
  status: "success" | "failed";
  refId: string;
  filedAt: string;
  whatsappSent: boolean;
  phone: string;
}

export interface TrustScoreComponents {
  paymentRate: number;
  consistency: number;
  volumeTrend: number;
  gstCompliance: number;
  returnRate: number;
}

export interface TrustScore {
  score: number;
  bucket: "Low" | "Medium" | "Good" | "Excellent";
  components: TrustScoreComponents;
  history: Array<{
    date: string;
    score: number;
  }>;
  lastUpdated: string;
}

export type InvoiceStatus = "PENDING" | "PAID" | "OVERDUE" | "FINANCED";

export interface Invoice {
  invoiceId: string;
  buyerName: string;
  buyerGstin: string;
  amount: number;
  dueDate: string;
  status: InvoiceStatus;
  overdueDays: number;
  advanceAmount: number;
  feeRate: number;
  repaid: boolean;
  createdAt: string;
}

export interface CreditOffer {
  offerId: string;
  invoiceId: string;
  advanceAmount: number;
  feeRate: number;
  repaymentTrigger: string;
  status: "pending_acceptance" | "accepted" | "rejected" | "expired";
  generatedAt: string;
}

export interface Notification {
  notifId: string;
  type: "gst" | "invoice" | "finance" | "transfer" | "alert";
  title: string;
  body: string;
  read: boolean;
  timestamp: string;
  actionUrl?: string;
}

export interface AuditEntry {
  logId: string;
  timestamp: string;
  actorType: "merchant" | "system" | "admin";
  actorId: string;
  action: string;
  entityId: string;
  amount?: number;
  outcome: "success" | "failed" | "pending";
  metadata: Record<string, unknown>;
}

export interface TransferInput {
  fromId: string;
  toUpiId: string;
  toName: string;
  amount: number;
  note?: string;
}

export interface GSTTransactionPatch {
  txId: string;
  hsnCode?: string;
  gstRate?: number;
  category?: GSTCategory;
}

export interface SendWhatsappAlertInput {
  merchantId: string;
  phone: string;
  message: string;
}

export interface RegisterAccountInput {
  name: string;
  phone: string;
  role: UserRole;
  pinHash: string;
  merchantId?: string;
  businessName?: string;
  gstin?: string;
  category?: string;
  city?: string;
}

export interface AuthResult {
  session: UserSession;
  merchant?: Merchant;
}

export interface AdapterInterface {
  getWalletBalance(merchantId: string): Promise<WalletBalance>;
  transfer(input: TransferInput): Promise<Transfer>;
  getCashflow(merchantId: string): Promise<{ projection: CashflowProjection; history: DailyRevenue[] }>;
  getGSTDraft(merchantId: string): Promise<GSTDraft>;
  updateGSTTransaction(merchantId: string, patch: GSTTransactionPatch): Promise<GSTDraft>;
  fileGST(merchantId: string): Promise<GSTFilingResult>;
  getTrustScore(merchantId: string): Promise<TrustScore>;
  getInvoices(merchantId: string): Promise<Invoice[]>;
  requestCreditOffer(merchantId: string, invoiceId: string): Promise<CreditOffer>;
  acceptCreditOffer(merchantId: string, offerId: string): Promise<CreditOffer>;
  getNotifications(merchantId: string): Promise<Notification[]>;
  getAuditLog(merchantId: string): Promise<AuditEntry[]>;
  getMerchantProfile(merchantId: string): Promise<Merchant>;
  resetDemo(): Promise<UserSession>;
  sendWhatsappAlert(input: SendWhatsappAlertInput): Promise<{ sent: boolean; queuedAt: string }>;

  getMerchants(): Promise<Merchant[]>;
  loginWithPin(merchantId: string, pinHash: string): Promise<AuthResult>;
  registerAccount(input: RegisterAccountInput): Promise<AuthResult>;
  markNotificationRead(merchantId: string, notifId: string): Promise<void>;
  markAllNotificationsRead(merchantId: string): Promise<void>;

  getDashboard?: (merchantId: string) => Promise<GSTDashboard>;
  getTransactions?: (merchantId: string) => Promise<GSTServiceTransaction[]>;
  getReviewQueue?: (merchantId: string) => Promise<GSTReviewQueueItem[]>;
  resolveReviewItem?: (queueId: string, payload: ResolveReviewItemPayload) => Promise<ResolveReviewItemResult>;
  generateGSTR1?: (merchantId: string) => Promise<GSTR1GenerationResult>;
  getGSTR1Draft?: (merchantId: string) => Promise<GSTR1Draft>;
  generateGSTR3B?: (merchantId: string) => Promise<GSTR3BGenerationResult>;
  getGSTR3BSummary?: (merchantId: string) => Promise<GSTR3BSummary>;

  scanBill?: (file: File) => Promise<OCRStructuredResult>;
  saveOcrResult?: (merchantId: string, structuredJson: OCRStructuredResult) => Promise<OCRSaveResult>;
  sendGstVoiceAudio?: (audioBlob: Blob, filename?: string) => Promise<GSTVoiceAudioResult>;
  sendGstVoiceText?: (query: string) => Promise<GSTVoiceTextResult>;
}
