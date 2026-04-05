import type {
  AdapterInterface,
  AuditEntry,
  AuthResult,
  CashflowProjection,
  CreditOffer,
  DailyRevenue,
  GSTDashboard,
  GSTDraft,
  GSTFilingResult,
  GSTR1Draft,
  GSTR1GenerationResult,
  GSTR3BGenerationResult,
  GSTR3BSummary,
  GSTReviewQueueItem,
  GSTServiceTransaction,
  GSTTransaction,
  GSTTransactionPatch,
  GSTVoiceAudioResult,
  GSTVoiceTextResult,
  Invoice,
  Merchant,
  Notification,
  OCRSaveResult,
  OCRStructuredResult,
  RegisterAccountInput,
  ResolveReviewItemPayload,
  ResolveReviewItemResult,
  SendWhatsappAlertInput,
  Transfer,
  TransferInput,
  TrustScore,
  UserSession,
  WalletBalance,
} from "@/src/adapters/types";
import { gstApiClient } from "@/src/lib/gst-api-client";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const PIN_HASH_1234 = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4";

interface ApiResult<T> {
  ok: boolean;
  status: number;
  data: T | null;
  error: string | null;
}

function parseError(payload: any, status: number): string {
  const detail = payload?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (detail && typeof detail === "object") {
    if (typeof detail.error === "string") {
      return detail.error;
    }
    return JSON.stringify(detail);
  }
  if (typeof payload?.error === "string") {
    return payload.error;
  }
  if (status >= 500) {
    return "Service unavailable";
  }
  return "Request failed";
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  try {
    const headers = {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    };

    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
    });

    let payload: any = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        data: null,
        error: parseError(payload, response.status),
      };
    }

    return {
      ok: true,
      status: response.status,
      data: payload as T,
      error: null,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      data: null,
      error: error instanceof Error ? error.message : "Network error",
    };
  }
}

async function postFormData<T>(path: string, formData: FormData): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      body: formData,
    });

    let payload: any = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }

    if (!response.ok) {
      throw new Error(parseError(payload, response.status));
    }

    return payload as T;
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : "Request failed");
  }
}

function ensureOrThrow<T>(result: ApiResult<T>): T {
  if (result.ok && result.data !== null) {
    return result.data;
  }
  if (result.status >= 500) {
    throw new Error("Service unavailable");
  }
  throw new Error(result.error || "Request failed");
}

function mapMerchant(row: any): Merchant {
  return {
    merchantId: String(row?.merchant_id ?? row?.merchantId ?? ""),
    name: String(row?.name ?? ""),
    gstin: String(row?.gstin ?? ""),
    businessName: String(row?.business_name ?? row?.businessName ?? row?.name ?? ""),
    category: String(row?.category ?? "Other"),
    phone: String(row?.phone ?? ""),
    kycStatus: (row?.kyc_status ?? row?.kycStatus ?? "pending") as Merchant["kycStatus"],
    createdAt: String(row?.created_at ?? row?.createdAt ?? new Date().toISOString()),
    walletBalance: Number(row?.wallet_balance ?? row?.walletBalance ?? 0),
  };
}

function mapInvoice(row: any): Invoice {
  return {
    invoiceId: String(row?.invoice_id ?? row?.invoiceId ?? ""),
    buyerName: String(row?.buyer_name ?? row?.buyerName ?? ""),
    buyerGstin: String(row?.buyer_gstin ?? row?.buyerGstin ?? ""),
    amount: Number(row?.amount ?? 0),
    dueDate: String(row?.due_date ?? row?.dueDate ?? new Date().toISOString()),
    status: String(row?.status ?? "PENDING") as Invoice["status"],
    overdueDays: Number(row?.overdue_days ?? row?.overdueDays ?? 0),
    advanceAmount: Number(row?.advance_amount ?? row?.advanceAmount ?? 0),
    feeRate: Number(row?.fee_rate ?? row?.feeRate ?? 0),
    repaid: Boolean(row?.repaid ?? false),
    createdAt: String(row?.created_at ?? row?.createdAt ?? new Date().toISOString()),
  };
}

function mapCreditOffer(row: any): CreditOffer {
  return {
    offerId: String(row?.offer_id ?? row?.offerId ?? ""),
    invoiceId: String(row?.invoice_id ?? row?.invoiceId ?? ""),
    advanceAmount: Number(row?.advance_amount ?? row?.advanceAmount ?? 0),
    feeRate: Number(row?.fee_rate ?? row?.feeRate ?? 2),
    repaymentTrigger: String(row?.repayment_trigger ?? row?.repaymentTrigger ?? "auto_deducted_on_buyer_payment"),
    status: String(row?.status ?? "pending_acceptance") as CreditOffer["status"],
    generatedAt: String(row?.generated_at ?? row?.generatedAt ?? new Date().toISOString()),
  };
}

function mapNotification(row: any): Notification {
  return {
    notifId: String(row?.notif_id ?? row?.notifId ?? ""),
    type: String(row?.type ?? "alert") as Notification["type"],
    title: String(row?.title ?? ""),
    body: String(row?.body ?? ""),
    read: Boolean(row?.read ?? false),
    timestamp: String(row?.timestamp ?? new Date().toISOString()),
    actionUrl: row?.action_url ?? row?.actionUrl,
  };
}

function mapAudit(row: any): AuditEntry {
  return {
    logId: String(row?.log_id ?? row?.logId ?? ""),
    timestamp: String(row?.timestamp ?? new Date().toISOString()),
    actorType: String(row?.actor_type ?? row?.actorType ?? "system") as AuditEntry["actorType"],
    actorId: String(row?.actor_id ?? row?.actorId ?? ""),
    action: String(row?.action ?? ""),
    entityId: String(row?.entity_id ?? row?.entityId ?? ""),
    amount: row?.amount == null ? undefined : Number(row.amount),
    outcome: String(row?.outcome ?? "success") as AuditEntry["outcome"],
    metadata: (row?.metadata && typeof row.metadata === "object" ? row.metadata : {}) as Record<string, unknown>,
  };
}

function mapGSTTransaction(row: any): GSTTransaction {
  return {
    txId: String(row?.tx_id ?? row?.txId ?? ""),
    description: String(row?.description ?? ""),
    amount: Number(row?.amount ?? 0),
    hsnCode: String(row?.hsn_code ?? row?.hsnCode ?? ""),
    gstRate: Number(row?.gst_rate ?? row?.gstRate ?? 0),
    cgst: Number(row?.cgst ?? 0),
    sgst: Number(row?.sgst ?? 0),
    category: String(row?.category ?? "B2B") as GSTTransaction["category"],
    reviewFlag: Boolean(row?.review_flag ?? row?.reviewFlag ?? false),
    editedByUser: Boolean(row?.edited_by_user ?? row?.editedByUser ?? false),
  };
}

function mapGSTDraft(payload: any): GSTDraft {
  const transactions = Array.isArray(payload?.transactions) ? payload.transactions.map(mapGSTTransaction) : [];
  return {
    merchantId: String(payload?.merchant_id ?? payload?.merchantId ?? ""),
    quarter: String(payload?.quarter ?? "Q1"),
    year: Number(payload?.year ?? new Date().getFullYear()),
    transactions,
    summary: {
      totalTaxable: Number(payload?.summary?.total_taxable ?? payload?.summary?.totalTaxable ?? 0),
      totalCGST: Number(payload?.summary?.total_cgst ?? payload?.summary?.totalCGST ?? 0),
      totalSGST: Number(payload?.summary?.total_sgst ?? payload?.summary?.totalSGST ?? 0),
      netLiability: Number(payload?.summary?.net_liability ?? payload?.summary?.netLiability ?? 0),
      flaggedCount: Number(payload?.summary?.flagged_count ?? payload?.summary?.flaggedCount ?? 0),
      totalCount: Number(payload?.summary?.total_count ?? payload?.summary?.totalCount ?? transactions.length),
    },
    generatedAt: String(payload?.generated_at ?? payload?.generatedAt ?? new Date().toISOString()),
  };
}

function mapTrustScore(payload: any): TrustScore {
  const history = Array.isArray(payload?.history)
    ? payload.history.map((row: any) => ({ date: String(row?.date ?? ""), score: Number(row?.score ?? 0) }))
    : [];

  return {
    score: Number(payload?.score ?? 0),
    bucket: String(payload?.bucket ?? "Low") as TrustScore["bucket"],
    components: {
      paymentRate: Number(payload?.components?.payment_rate ?? payload?.components?.paymentRate ?? 0),
      consistency: Number(payload?.components?.consistency ?? 0),
      volumeTrend: Number(payload?.components?.volume_trend ?? payload?.components?.volumeTrend ?? 0),
      gstCompliance: Number(payload?.components?.gst_compliance ?? payload?.components?.gstCompliance ?? 0),
      returnRate: Number(payload?.components?.return_rate ?? payload?.components?.returnRate ?? 0),
    },
    history,
    lastUpdated: String(payload?.computed_at ?? payload?.last_updated ?? payload?.lastUpdated ?? new Date().toISOString()),
  };
}

function mapSession(payload: any): UserSession {
  return {
    userId: String(payload?.user_id ?? payload?.userId ?? ""),
    name: String(payload?.name ?? ""),
    phone: String(payload?.phone ?? ""),
    role: String(payload?.role ?? "merchant") as UserSession["role"],
    merchantId: payload?.merchant_id ?? payload?.merchantId,
    token: String(payload?.token ?? ""),
    expiresAt: String(payload?.expires_at ?? payload?.expiresAt ?? new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()),
  };
}

function mapProjection(payload: any): CashflowProjection {
  return {
    p30: {
      amount: Number(payload?.p30?.amount ?? 0),
      confidence: Number(payload?.p30?.confidence ?? 90),
    },
    p60: {
      amount: Number(payload?.p60?.amount ?? 0),
      confidence: Number(payload?.p60?.confidence ?? 82),
    },
    p90: {
      amount: Number(payload?.p90?.amount ?? 0),
      confidence: Number(payload?.p90?.confidence ?? 75),
    },
    generatedAt: new Date().toISOString(),
  };
}

function mapDailyRow(row: any): DailyRevenue {
  return {
    date: String(row?.date ?? ""),
    amount: Number(row?.amount ?? 0),
    transactionCount: Number(row?.transaction_count ?? row?.transactionCount ?? 0),
    isProjected: Boolean(row?.is_projected ?? row?.isProjected ?? false),
    lowerBound: Number(row?.lower_bound ?? row?.lowerBound ?? Number(row?.amount ?? 0) * 0.9),
    upperBound: Number(row?.upper_bound ?? row?.upperBound ?? Number(row?.amount ?? 0) * 1.1),
  };
}

function mapGSTServiceTransaction(row: any): GSTServiceTransaction {
  return {
    txId: String(row?.tx_id ?? row?.txId ?? ""),
    description: String(row?.description ?? ""),
    amount: Number(row?.amount ?? 0),
    hsnCode: String(row?.hsn_code ?? row?.hsnCode ?? ""),
    gstRate: Number(row?.gst_rate ?? row?.gstRate ?? 0),
    gstCategory: String(row?.gst_category ?? row?.gstCategory ?? row?.category ?? "B2B") as GSTServiceTransaction["gstCategory"],
    cgst: Number(row?.cgst ?? 0),
    sgst: Number(row?.sgst ?? 0),
    reviewFlag: Boolean(row?.review_flag ?? row?.reviewFlag ?? false),
    status: String(row?.status ?? "ready") as GSTServiceTransaction["status"],
  };
}

function mapGSTDashboard(payload: any): GSTDashboard {
  return {
    merchantId: String(payload?.merchant_id ?? payload?.merchantId ?? ""),
    summary: {
      totalTransactions: Number(payload?.summary?.total_transactions ?? payload?.summary?.totalTransactions ?? 0),
      flaggedTransactions: Number(payload?.summary?.flagged_transactions ?? payload?.summary?.flaggedTransactions ?? 0),
      totalTaxable: Number(payload?.summary?.total_taxable ?? payload?.summary?.totalTaxable ?? 0),
      totalCGST: Number(payload?.summary?.total_cgst ?? payload?.summary?.totalCGST ?? 0),
      totalSGST: Number(payload?.summary?.total_sgst ?? payload?.summary?.totalSGST ?? 0),
      netLiability: Number(payload?.summary?.net_liability ?? payload?.summary?.netLiability ?? 0),
      lastGeneratedAt: String(payload?.summary?.last_generated_at ?? payload?.summary?.lastGeneratedAt ?? new Date().toISOString()),
    },
    gstr1Generated: Boolean(payload?.gstr1_generated ?? payload?.gstr1Generated ?? false),
    gstr3bGenerated: Boolean(payload?.gstr3b_generated ?? payload?.gstr3bGenerated ?? false),
  };
}

function mapReviewQueueItem(row: any): GSTReviewQueueItem {
  return {
    queueId: String(row?.queue_id ?? row?.queueId ?? ""),
    merchantId: String(row?.merchant_id ?? row?.merchantId ?? ""),
    txId: String(row?.tx_id ?? row?.txId ?? ""),
    description: String(row?.description ?? ""),
    amount: Number(row?.amount ?? 0),
    currentHSN: String(row?.current_hsn ?? row?.currentHSN ?? ""),
    currentGSTRate: Number(row?.current_gst_rate ?? row?.currentGSTRate ?? 0),
    gstCategory: String(row?.gst_category ?? row?.gstCategory ?? "B2B") as GSTReviewQueueItem["gstCategory"],
    reviewFlag: Boolean(row?.review_flag ?? row?.reviewFlag ?? false),
    status: String(row?.status ?? "needs_review") as GSTReviewQueueItem["status"],
  };
}

function mapGSTR1Row(row: any): GSTR1Draft["table4"][number] {
  return {
    txId: String(row?.tx_id ?? row?.txId ?? ""),
    description: String(row?.description ?? ""),
    amount: Number(row?.amount ?? 0),
    hsnCode: String(row?.hsn_code ?? row?.hsnCode ?? ""),
    gstRate: Number(row?.gst_rate ?? row?.gstRate ?? 0),
    cgst: Number(row?.cgst ?? 0),
    sgst: Number(row?.sgst ?? 0),
  };
}

function mapGSTR1Draft(payload: any): GSTR1Draft {
  const table4 = Array.isArray(payload?.table_4) ? payload.table_4.map(mapGSTR1Row) : [];
  const table5 = Array.isArray(payload?.table_5) ? payload.table_5.map(mapGSTR1Row) : [];
  const table7 = Array.isArray(payload?.table_7) ? payload.table_7.map(mapGSTR1Row) : [];

  return {
    merchantId: String(payload?.merchant_id ?? payload?.merchantId ?? ""),
    generatedAt: String(payload?.generated_at ?? payload?.generatedAt ?? new Date().toISOString()),
    table4,
    table5,
    table7,
    summary: {
      totalRecords: Number(payload?.summary?.total_records ?? payload?.summary?.totalRecords ?? 0),
      totalTaxableValue: Number(payload?.summary?.total_taxable_value ?? payload?.summary?.totalTaxableValue ?? 0),
      totalTax: Number(payload?.summary?.total_tax ?? payload?.summary?.totalTax ?? 0),
      b2bRecords: Number(payload?.summary?.b2b_records ?? payload?.summary?.b2bRecords ?? table4.length),
      b2cRecords: Number(payload?.summary?.b2c_records ?? payload?.summary?.b2cRecords ?? table5.length),
      exemptRecords: Number(payload?.summary?.exempt_records ?? payload?.summary?.exemptRecords ?? table7.length),
    },
  };
}

function mapGSTR3BSummary(payload: any): GSTR3BSummary {
  return {
    merchantId: String(payload?.merchant_id ?? payload?.merchantId ?? ""),
    generatedAt: String(payload?.generated_at ?? payload?.generatedAt ?? new Date().toISOString()),
    taxableValue: Number(payload?.taxable_value ?? payload?.taxableValue ?? 0),
    exemptValue: Number(payload?.exempt_value ?? payload?.exemptValue ?? 0),
    totalCGST: Number(payload?.total_cgst ?? payload?.totalCGST ?? 0),
    totalSGST: Number(payload?.total_sgst ?? payload?.totalSGST ?? 0),
    itcAvailable: Number(payload?.itc_available ?? payload?.itcAvailable ?? 0),
    netPayable: Number(payload?.net_payable ?? payload?.netPayable ?? 0),
    recordCount: Number(payload?.record_count ?? payload?.recordCount ?? 0),
  };
}

function mapOCRStructured(payload: any): OCRStructuredResult {
  const items = Array.isArray(payload?.items)
    ? payload.items.map((item: any) => ({
        description: String(item?.description ?? ""),
        quantity: item?.quantity == null ? null : Number(item.quantity),
        amount: Number(item?.amount ?? 0),
      }))
    : [];

  return {
    vendorName: String(payload?.vendor_name ?? payload?.vendorName ?? ""),
    vendorGstin: String(payload?.vendor_gstin ?? payload?.vendorGstin ?? ""),
    items,
    grandTotal: Number(payload?.grand_total ?? payload?.grandTotal ?? 0),
  };
}

export const liveAdapter: AdapterInterface = {
  async getWalletBalance(merchantId: string): Promise<WalletBalance> {
    const result = await apiFetch<any>(`/api/check-balance?merchant_id=${encodeURIComponent(merchantId)}`);
    if (!result.ok) {
      if (result.status === 404) {
        return { balance: 0, currency: "INR", lastUpdated: new Date().toISOString() };
      }
      throw new Error(result.error || "Unable to fetch wallet balance");
    }
    const payload = result.data || {};
    return {
      balance: Number(payload.balance ?? 0),
      currency: String(payload.currency ?? "INR"),
      lastUpdated: String(payload.last_updated ?? payload.lastUpdated ?? new Date().toISOString()),
    };
  },

  async transfer(input: TransferInput): Promise<Transfer> {
    const result = await apiFetch<any>("/api/transfer", {
      method: "POST",
      body: JSON.stringify({
        from_id: input.fromId,
        to_upi_id: input.toUpiId,
        amount: input.amount,
        note: input.note ?? "",
      }),
    });

    if (!result.ok) {
      throw new Error(result.error || "Transfer failed");
    }

    const payload = result.data || {};
    if (payload.status === "pending_approval") {
      return {
        txId: String(payload.transfer_id ?? ""),
        fromId: input.fromId,
        toUpiId: input.toUpiId,
        toName: input.toName,
        amount: input.amount,
        note: input.note ?? "",
        status: "pending",
        timestamp: new Date().toISOString(),
        auditId: "",
      };
    }

    return {
      txId: String(payload.tx_id ?? payload.txId ?? ""),
      fromId: String(payload.from_id ?? input.fromId),
      toUpiId: String(payload.to_upi_id ?? input.toUpiId),
      toName: input.toName,
      amount: Number(payload.amount ?? input.amount),
      note: String(payload.note ?? input.note ?? ""),
      status: "success",
      timestamp: String(payload.timestamp ?? new Date().toISOString()),
      auditId: String(payload.audit_id ?? ""),
    };
  },

  async getCashflow(merchantId: string): Promise<{ projection: CashflowProjection; history: DailyRevenue[] }> {
    const analyzeResult = await apiFetch<any>(`/cashflow/analyze/${encodeURIComponent(merchantId)}`, { method: "POST" });
    if (!analyzeResult.ok) {
      throw new Error(analyzeResult.error || "Unable to analyze cashflow");
    }

    const analysis = analyzeResult.data || {};
    const projection = mapProjection(analysis.projections || {});

    const historyResult = await apiFetch<any>(`/cashflow/history/${encodeURIComponent(merchantId)}?days=180`);
    const historyRows = historyResult.ok
      ? Array.isArray(historyResult.data?.daily_history)
        ? historyResult.data.daily_history
        : []
      : [];

    const historical = historyRows.map(mapDailyRow).map((row: DailyRevenue) => ({ ...row, isProjected: false }));
    const projectedFromAnalysis = Array.isArray(analysis.daily_history)
      ? analysis.daily_history.filter((row: any) => row?.is_projected || row?.isProjected).map(mapDailyRow)
      : [];

    const history = [...historical, ...projectedFromAnalysis];
    return { projection, history };
  },

  async getGSTDraft(merchantId: string): Promise<GSTDraft> {
    const result = await apiFetch<any>(`/api/gst-draft?merchant_id=${encodeURIComponent(merchantId)}`);
    return mapGSTDraft(ensureOrThrow(result));
  },

  async updateGSTTransaction(merchantId: string, patch: GSTTransactionPatch): Promise<GSTDraft> {
    const result = await apiFetch<any>("/api/gst-update-tx", {
      method: "POST",
      body: JSON.stringify({
        merchant_id: merchantId,
        tx_id: patch.txId,
        hsn_code: patch.hsnCode,
        gst_rate: patch.gstRate,
        category: patch.category,
      }),
    });
    return mapGSTDraft(ensureOrThrow(result));
  },

  async fileGST(merchantId: string): Promise<GSTFilingResult> {
    const result = await apiFetch<any>("/api/gst-file", {
      method: "POST",
      body: JSON.stringify({ merchant_id: merchantId }),
    });
    const payload = ensureOrThrow(result);
    return {
      status: String(payload.status ?? "failed") as GSTFilingResult["status"],
      refId: String(payload.ref_id ?? payload.refId ?? ""),
      filedAt: String(payload.filed_at ?? payload.filedAt ?? new Date().toISOString()),
      whatsappSent: Boolean(payload.whatsapp_sent ?? payload.whatsappSent ?? false),
      phone: String(payload.phone ?? ""),
    };
  },

  async getTrustScore(merchantId: string): Promise<TrustScore> {
    const result = await apiFetch<any>(`/api/trustscore?merchant_id=${encodeURIComponent(merchantId)}`);
    return mapTrustScore(ensureOrThrow(result));
  },

  async getInvoices(merchantId: string): Promise<Invoice[]> {
    const result = await apiFetch<any>(`/api/invoices?merchant_id=${encodeURIComponent(merchantId)}&status=ALL&page=1&page_size=100`);
    if (!result.ok) {
      if (result.status === 404) {
        return [];
      }
      throw new Error(result.error || "Unable to fetch invoices");
    }
    const rows = Array.isArray(result.data?.invoices) ? result.data.invoices : [];
    return rows.map(mapInvoice);
  },

  async requestCreditOffer(merchantId: string, invoiceId: string): Promise<CreditOffer> {
    const result = await apiFetch<any>("/api/credit-offer", {
      method: "POST",
      body: JSON.stringify({ merchant_id: merchantId, invoice_id: invoiceId }),
    });
    return mapCreditOffer(ensureOrThrow(result));
  },

  async acceptCreditOffer(merchantId: string, offerId: string): Promise<CreditOffer> {
    const result = await apiFetch<any>("/api/credit-accept", {
      method: "POST",
      body: JSON.stringify({ merchant_id: merchantId, offer_id: offerId }),
    });
    const payload = ensureOrThrow(result);
    return {
      offerId,
      invoiceId: String(payload.invoice_id ?? payload.invoiceId ?? ""),
      advanceAmount: Number(payload.advance_amount ?? payload.advanceAmount ?? 0),
      feeRate: 2,
      repaymentTrigger: "auto_deducted_on_buyer_payment",
      status: "accepted",
      generatedAt: String(payload.accepted_at ?? payload.generated_at ?? new Date().toISOString()),
    };
  },

  async getNotifications(merchantId: string): Promise<Notification[]> {
    const result = await apiFetch<any>(`/api/notifications?merchant_id=${encodeURIComponent(merchantId)}&unread_only=false&page=1&page_size=200`);
    if (!result.ok) {
      if (result.status === 404) {
        return [];
      }
      throw new Error(result.error || "Unable to fetch notifications");
    }
    const rows = Array.isArray(result.data?.notifications) ? result.data.notifications : [];
    return rows.map(mapNotification);
  },

  async getAuditLog(merchantId: string): Promise<AuditEntry[]> {
    const result = await apiFetch<any>(`/api/audit-log?merchant_id=${encodeURIComponent(merchantId)}&page=1&page_size=200`);
    if (!result.ok) {
      if (result.status === 404) {
        return [];
      }
      throw new Error(result.error || "Unable to fetch audit log");
    }
    const rows = Array.isArray(result.data?.entries) ? result.data.entries : [];
    return rows.map(mapAudit);
  },

  async getMerchantProfile(merchantId: string): Promise<Merchant> {
    const result = await apiFetch<any>(`/api/merchants/${encodeURIComponent(merchantId)}`);
    const payload = ensureOrThrow(result);
    return mapMerchant(payload.merchant ?? payload);
  },

  async resetDemo(): Promise<UserSession> {
    await apiFetch<any>("/api/reset-demo", { method: "POST" });
    const login = await apiFetch<any>("/api/login", {
      method: "POST",
      body: JSON.stringify({ merchant_id: "seller_a", pin_hash: PIN_HASH_1234 }),
    });
    const payload = ensureOrThrow(login);
    return mapSession(payload.session ?? payload);
  },

  async sendWhatsappAlert(input: SendWhatsappAlertInput): Promise<{ sent: boolean; queuedAt: string }> {
    const result = await apiFetch<any>("/api/whatsapp-alert", {
      method: "POST",
      body: JSON.stringify({
        merchant_id: input.merchantId,
        phone: input.phone,
        message: input.message,
      }),
    });
    const payload = ensureOrThrow(result);
    return {
      sent: Boolean(payload.sent ?? false),
      queuedAt: String(payload.queuedAt ?? payload.queued_at ?? new Date().toISOString()),
    };
  },

  async getMerchants(): Promise<Merchant[]> {
    try {
      const payload = await gstApiClient.get<any>("/api/merchants");
      const rows = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.merchants)
          ? payload.merchants
          : [];
      return rows.map(mapMerchant);
    } catch {
      const result = await apiFetch<any>("/api/merchants?page=1&page_size=200");
      if (!result.ok) {
        throw new Error(result.error || "Unable to fetch merchants");
      }
      const rows = Array.isArray(result.data)
        ? result.data
        : Array.isArray(result.data?.merchants)
          ? result.data.merchants
          : [];
      return rows.map(mapMerchant);
    }
  },

  async getDashboard(merchantId: string): Promise<GSTDashboard> {
    const payload = await gstApiClient.get<any>(`/api/dashboard/${encodeURIComponent(merchantId)}`);
    return mapGSTDashboard(payload);
  },

  async getTransactions(merchantId: string): Promise<GSTServiceTransaction[]> {
    const payload = await gstApiClient.get<any[]>(`/api/transactions/${encodeURIComponent(merchantId)}`);
    return (Array.isArray(payload) ? payload : []).map(mapGSTServiceTransaction);
  },

  async getReviewQueue(merchantId: string): Promise<GSTReviewQueueItem[]> {
    const payload = await gstApiClient.get<any[]>(`/api/review/queue/${encodeURIComponent(merchantId)}`);
    return (Array.isArray(payload) ? payload : []).map(mapReviewQueueItem);
  },

  async resolveReviewItem(queueId: string, payload: ResolveReviewItemPayload): Promise<ResolveReviewItemResult> {
    const data = await gstApiClient.put<any>(`/api/review/${encodeURIComponent(queueId)}/resolve`, {
      hsn_code: payload.hsnCode,
      gst_rate: payload.gstRate,
      status: payload.status,
    });

    return {
      status: String(data?.status ?? "updated") as ResolveReviewItemResult["status"],
      queueId: String(data?.queue_id ?? data?.queueId ?? queueId),
      merchantId: String(data?.merchant_id ?? data?.merchantId ?? ""),
      txId: String(data?.tx_id ?? data?.txId ?? ""),
      updatedAt: String(data?.updated_at ?? data?.updatedAt ?? new Date().toISOString()),
    };
  },

  async generateGSTR1(merchantId: string): Promise<GSTR1GenerationResult> {
    const payload = await gstApiClient.post<any>(`/api/gstr1/generate/${encodeURIComponent(merchantId)}`);
    return {
      status: String(payload?.status ?? "completed") as GSTR1GenerationResult["status"],
      merchantId: String(payload?.merchant_id ?? payload?.merchantId ?? merchantId),
      generatedAt: String(payload?.generated_at ?? payload?.generatedAt ?? new Date().toISOString()),
      recordCount: Number(payload?.record_count ?? payload?.recordCount ?? 0),
    };
  },

  async getGSTR1Draft(merchantId: string): Promise<GSTR1Draft> {
    const payload = await gstApiClient.get<any>(`/api/gstr1/draft/${encodeURIComponent(merchantId)}`);
    return mapGSTR1Draft(payload);
  },

  async generateGSTR3B(merchantId: string): Promise<GSTR3BGenerationResult> {
    const payload = await gstApiClient.post<any>(`/api/gstr3b/generate/${encodeURIComponent(merchantId)}`);
    return {
      status: String(payload?.status ?? "completed") as GSTR3BGenerationResult["status"],
      merchantId: String(payload?.merchant_id ?? payload?.merchantId ?? merchantId),
      generatedAt: String(payload?.generated_at ?? payload?.generatedAt ?? new Date().toISOString()),
      recordCount: Number(payload?.record_count ?? payload?.recordCount ?? 0),
    };
  },

  async getGSTR3BSummary(merchantId: string): Promise<GSTR3BSummary> {
    const payload = await gstApiClient.get<any>(`/api/gstr3b/summary/${encodeURIComponent(merchantId)}`);
    return mapGSTR3BSummary(payload);
  },

  async scanBill(file: File): Promise<OCRStructuredResult> {
    const formData = new FormData();
    formData.append("bill", file);

    const payload = await postFormData<any>("/api/ocr-bill", formData);
    if (String(payload?.status ?? "").toLowerCase() !== "success") {
      throw new Error(String(payload?.message ?? "Bill scan failed"));
    }
    return mapOCRStructured(payload?.structured_json ?? {});
  },

  async saveOcrResult(merchantId: string, structuredJson: OCRStructuredResult): Promise<OCRSaveResult> {
    const result = await apiFetch<any>("/api/ocr-save", {
      method: "POST",
      body: JSON.stringify({
        merchant_id: merchantId,
        structured_json: {
          vendor_name: structuredJson.vendorName,
          vendor_gstin: structuredJson.vendorGstin,
          items: structuredJson.items,
          grand_total: structuredJson.grandTotal,
        },
      }),
    });
    const payload = ensureOrThrow(result);
    return {
      status: "success",
      saved: Boolean(payload?.saved ?? true),
      savedAt: String(payload?.saved_at ?? payload?.savedAt ?? new Date().toISOString()),
    };
  },

  async sendGstVoiceAudio(audioBlob: Blob, filename = "voice.webm"): Promise<GSTVoiceAudioResult> {
    const formData = new FormData();
    formData.append("audio", audioBlob, filename);

    const payload = await postFormData<any>("/api/gst-voice/audio", formData);
    return {
      transcription: String(payload?.transcription ?? ""),
      responseText: String(payload?.response_text ?? payload?.responseText ?? ""),
      audioBase64: payload?.audio_base64 ?? payload?.audioBase64 ?? null,
    };
  },

  async sendGstVoiceText(query: string): Promise<GSTVoiceTextResult> {
    const result = await apiFetch<any>("/api/gst-voice/text", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
    const payload = ensureOrThrow(result);
    return {
      responseText: String(payload?.response_text ?? payload?.responseText ?? ""),
    };
  },

  async loginWithPin(merchantId: string, pinHash: string): Promise<AuthResult> {
    const result = await apiFetch<any>("/api/login", {
      method: "POST",
      body: JSON.stringify({ merchant_id: merchantId, pin_hash: pinHash }),
    });
    const payload = ensureOrThrow(result);
    return {
      session: mapSession(payload.session ?? payload),
      merchant: payload.merchant ? mapMerchant(payload.merchant) : undefined,
    };
  },

  async registerAccount(input: RegisterAccountInput): Promise<AuthResult> {
    const result = await apiFetch<any>("/api/register", {
      method: "POST",
      body: JSON.stringify({
        name: input.name,
        phone: input.phone,
        role: input.role,
        pin_hash: input.pinHash,
        merchant_id: input.merchantId,
        business_name: input.businessName,
        gstin: input.gstin,
        category: input.category,
        city: input.city,
      }),
    });
    const payload = ensureOrThrow(result);
    return {
      session: mapSession(payload.session ?? payload),
      merchant: payload.merchant ? mapMerchant(payload.merchant) : undefined,
    };
  },

  async markNotificationRead(merchantId: string, notifId: string): Promise<void> {
    const result = await apiFetch<any>(`/api/notifications/${encodeURIComponent(notifId)}/read?merchant_id=${encodeURIComponent(merchantId)}`, {
      method: "POST",
    });
    ensureOrThrow(result);
  },

  async markAllNotificationsRead(merchantId: string): Promise<void> {
    const result = await apiFetch<any>("/api/notifications/read-all", {
      method: "POST",
      body: JSON.stringify({ merchant_id: merchantId }),
    });
    ensureOrThrow(result);
  },
};

export function getLiveAdapter(): AdapterInterface {
  return liveAdapter;
}
