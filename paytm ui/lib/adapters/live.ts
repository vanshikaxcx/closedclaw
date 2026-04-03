import { getMockAdapter } from "@/lib/adapters/mock";
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
  WalletPayload,
  TrustScorePayload,
} from "@/lib/adapters/types";

const mock = getMockAdapter();

async function safeFetch<T>(input: RequestInfo, init?: RequestInit): Promise<T | null> {
  try {
    const response = await fetch(input, init);
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

const liveAdapter: DataAdapter = {
  mode: "live",

  async login(merchantId: string, pin: string): Promise<AuthSession> {
    // Placeholder mode until real auth endpoint is wired.
    return mock.login(merchantId, pin);
  },

  async resetDemo(): Promise<AuthSession> {
    const payload = await safeFetch<{ session?: AuthSession }>("/api/reset-demo", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (payload?.session) {
      return payload.session;
    }

    return mock.resetDemo();
  },

  async getTrustScore(merchantId: string): Promise<TrustScorePayload> {
    const payload = await safeFetch<TrustScorePayload>(`/api/trustscore?merchant_id=${merchantId}`);
    if (payload) {
      return payload;
    }
    return mock.getTrustScore(merchantId);
  },

  async getGstDraft(merchantId: string): Promise<GstDraftPayload> {
    const payload = await safeFetch<GstDraftPayload>(`/api/gst-draft?merchant_id=${merchantId}`);
    if (payload) {
      return payload;
    }
    return mock.getGstDraft(merchantId);
  },

  async updateGstTransaction(
    merchantId: string,
    txId: string,
    patch: Partial<Pick<GstTransactionRow, "gstRate" | "hsnCode" | "gstCategory">>,
  ): Promise<GstDraftPayload> {
    const payload = await safeFetch<GstDraftPayload>("/api/gst-update-tx", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ merchant_id: merchantId, tx_id: txId, ...patch }),
    });
    if (payload) {
      return payload;
    }
    return mock.updateGstTransaction(merchantId, txId, patch);
  },

  async fileGstReturn(merchantId: string): Promise<{ filingId: string; whatsappSentTo: string }> {
    const payload = await safeFetch<{ filingId: string; whatsappSentTo: string }>("/api/gst-file", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ merchant_id: merchantId }),
    });
    if (payload) {
      return payload;
    }
    return mock.fileGstReturn(merchantId);
  },

  async getInvoices(merchantId: string): Promise<InvoiceRecord[]> {
    const payload = await safeFetch<InvoiceRecord[]>(`/api/invoices?merchant_id=${merchantId}`);
    if (payload) {
      return payload;
    }
    return mock.getInvoices(merchantId);
  },

  async requestCreditOffer(merchantId: string, invoiceId: string): Promise<CreditOfferPayload> {
    const payload = await safeFetch<CreditOfferPayload>("/api/credit-offer", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ merchant_id: merchantId, invoice_id: invoiceId }),
    });
    if (payload) {
      return payload;
    }
    return mock.requestCreditOffer(merchantId, invoiceId);
  },

  async acceptCreditOffer(
    merchantId: string,
    offerId: string,
  ): Promise<{ disbursalId: string; whatsappSentTo: string }> {
    const payload = await safeFetch<{ disbursalId: string; whatsappSentTo: string }>("/api/credit-accept", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ merchant_id: merchantId, offer_id: offerId }),
    });
    if (payload) {
      return payload;
    }
    return mock.acceptCreditOffer(merchantId, offerId);
  },

  async applyRepayment(merchantId: string, invoiceId: string): Promise<{ repaymentId: string }> {
    // Placeholder until repayment endpoint is exposed.
    return mock.applyRepayment(merchantId, invoiceId);
  },

  async getCashflow(merchantId: string, windowDays: 30 | 60 | 90): Promise<CashflowPayload> {
    const payload = await safeFetch<CashflowPayload>(`/api/cashflow-${windowDays}?merchant_id=${merchantId}`);
    if (payload) {
      return payload;
    }
    return mock.getCashflow(merchantId, windowDays);
  },

  async getWallet(merchantId: string): Promise<WalletPayload> {
    const payload = await safeFetch<{ balance: number }>(`/api/check-balance?merchant_id=${merchantId}`);
    if (payload) {
      return {
        balance: payload.balance,
        lastUpdatedAt: new Date().toISOString(),
      };
    }
    return mock.getWallet(merchantId);
  },

  async transferFunds(merchantId: string, to: string, amount: number): Promise<TransferResult> {
    const payload = await safeFetch<TransferResult>("/api/transfer", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ merchant_id: merchantId, to, amount }),
    });
    if (payload) {
      return payload;
    }
    return mock.transferFunds(merchantId, to, amount);
  },

  async getAuditLog(merchantId: string): Promise<AuditEvent[]> {
    const payload = await safeFetch<AuditEvent[]>(`/api/audit-log?merchant_id=${merchantId}`);
    if (payload) {
      return payload;
    }
    return mock.getAuditLog(merchantId);
  },

  async getNotifications(merchantId: string): Promise<AppNotification[]> {
    const payload = await safeFetch<AppNotification[]>(`/api/notifications?merchant_id=${merchantId}`);
    if (payload) {
      return payload;
    }
    return mock.getNotifications(merchantId);
  },

  async getMerchants(): Promise<MerchantSummary[]> {
    const payload = await safeFetch<MerchantSummary[]>("/api/merchants");
    if (payload) {
      return payload;
    }
    return mock.getMerchants();
  },

  async getMerchantOverview(merchantId: string): Promise<MerchantOverview> {
    const payload = await safeFetch<MerchantOverview>(`/api/merchants/${merchantId}`);
    if (payload) {
      return payload;
    }
    return mock.getMerchantOverview(merchantId);
  },
};

export function getLiveAdapter(): DataAdapter {
  return liveAdapter;
}
