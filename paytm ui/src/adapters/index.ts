import { getLiveAdapter } from "@/src/adapters/live";
import { getMockAdapter } from "@/src/adapters/mock";
import type {
	AdapterInterface,
	GSTR1Draft,
	GSTR1GenerationResult,
	GSTR3BGenerationResult,
	GSTR3BSummary,
	GSTDashboard,
	GSTDraft,
	GSTReviewQueueItem,
	GSTServiceTransaction,
	ResolveReviewItemPayload,
	ResolveReviewItemResult,
} from "@/src/adapters/types";

const mode = (process.env.NEXT_PUBLIC_ADAPTER_MODE ?? "mock").toLowerCase();
const DEMO_MERCHANT_ID = "seller_a";
const FORCE_SINGLE_DEMO_MERCHANT = true;

const liveAdapter = getLiveAdapter();
const mockAdapter = getMockAdapter();
const selectedAdapter: AdapterInterface = mode === "live" ? liveAdapter : mockAdapter;

function nowIso(): string {
	return new Date().toISOString();
}

function normalizeMerchantId(_merchantId: string): string {
	return DEMO_MERCHANT_ID;
}

function mapDraftToDashboard(draft: GSTDraft): GSTDashboard {
	return {
		merchantId: DEMO_MERCHANT_ID,
		summary: {
			totalTransactions: draft.summary.totalCount,
			flaggedTransactions: draft.summary.flaggedCount,
			totalTaxable: draft.summary.totalTaxable,
			totalCGST: draft.summary.totalCGST,
			totalSGST: draft.summary.totalSGST,
			netLiability: draft.summary.netLiability,
			lastGeneratedAt: draft.generatedAt,
		},
		gstr1Generated: true,
		gstr3bGenerated: true,
	};
}

function mapDraftToTransactions(draft: GSTDraft): GSTServiceTransaction[] {
	return draft.transactions.map((row) => ({
		txId: row.txId,
		description: row.description,
		amount: row.amount,
		hsnCode: row.hsnCode,
		gstRate: row.gstRate,
		gstCategory: row.category,
		cgst: row.cgst,
		sgst: row.sgst,
		reviewFlag: row.reviewFlag,
		status: row.reviewFlag ? "needs_review" : "ready",
	}));
}

function mapDraftToReviewQueue(draft: GSTDraft): GSTReviewQueueItem[] {
	return draft.transactions
		.filter((row) => row.reviewFlag)
		.map((row) => ({
			queueId: `${DEMO_MERCHANT_ID}:${row.txId}`,
			merchantId: DEMO_MERCHANT_ID,
			txId: row.txId,
			description: row.description,
			amount: row.amount,
			currentHSN: row.hsnCode,
			currentGSTRate: row.gstRate,
			gstCategory: row.category,
			reviewFlag: true,
			status: "needs_review",
		}));
}

function parseQueueTxId(queueId: string): string {
	const parts = queueId.split(":");
	return parts.length > 1 ? parts[1] : queueId;
}

function toGstr1Draft(draft: GSTDraft): GSTR1Draft {
	const table4 = draft.transactions
		.filter((row) => row.category === "B2B")
		.map((row) => ({
			txId: row.txId,
			description: row.description,
			amount: row.amount,
			hsnCode: row.hsnCode,
			gstRate: row.gstRate,
			cgst: row.cgst,
			sgst: row.sgst,
		}));

	const table5 = draft.transactions
		.filter((row) => row.category === "B2C_LOCAL" || row.category === "B2C_INTERSTATE")
		.map((row) => ({
			txId: row.txId,
			description: row.description,
			amount: row.amount,
			hsnCode: row.hsnCode,
			gstRate: row.gstRate,
			cgst: row.cgst,
			sgst: row.sgst,
		}));

	const table7 = draft.transactions
		.filter((row) => row.category === "EXEMPT")
		.map((row) => ({
			txId: row.txId,
			description: row.description,
			amount: row.amount,
			hsnCode: row.hsnCode,
			gstRate: row.gstRate,
			cgst: row.cgst,
			sgst: row.sgst,
		}));

	const totalTax = draft.transactions.reduce((sum, row) => sum + row.cgst + row.sgst, 0);

	return {
		merchantId: DEMO_MERCHANT_ID,
		generatedAt: nowIso(),
		table4,
		table5,
		table7,
		summary: {
			totalRecords: draft.transactions.length,
			totalTaxableValue: draft.summary.totalTaxable,
			totalTax,
			b2bRecords: table4.length,
			b2cRecords: table5.length,
			exemptRecords: table7.length,
		},
	};
}

function toGstr3bSummary(draft: GSTDraft): GSTR3BSummary {
	const taxableValue = draft.transactions
		.filter((row) => row.category !== "EXEMPT")
		.reduce((sum, row) => sum + row.amount, 0);

	const exemptValue = draft.transactions
		.filter((row) => row.category === "EXEMPT")
		.reduce((sum, row) => sum + row.amount, 0);

	const totalCGST = draft.transactions.reduce((sum, row) => sum + row.cgst, 0);
	const totalSGST = draft.transactions.reduce((sum, row) => sum + row.sgst, 0);
	const itcAvailable = 0;

	return {
		merchantId: DEMO_MERCHANT_ID,
		generatedAt: nowIso(),
		taxableValue,
		exemptValue,
		totalCGST,
		totalSGST,
		itcAvailable,
		netPayable: totalCGST + totalSGST - itcAvailable,
		recordCount: draft.transactions.length,
	};
}

const demoAdapter: AdapterInterface = {
	async getWalletBalance(merchantId) {
		return mockAdapter.getWalletBalance(normalizeMerchantId(merchantId));
	},

	async transfer(input) {
		return mockAdapter.transfer({
			...input,
			fromId: DEMO_MERCHANT_ID,
		});
	},

	async getCashflow(merchantId) {
		return mockAdapter.getCashflow(normalizeMerchantId(merchantId));
	},

	async getGSTDraft(merchantId) {
		return mockAdapter.getGSTDraft(normalizeMerchantId(merchantId));
	},

	async updateGSTTransaction(merchantId, patch) {
		return mockAdapter.updateGSTTransaction(normalizeMerchantId(merchantId), patch);
	},

	async fileGST(merchantId) {
		return mockAdapter.fileGST(normalizeMerchantId(merchantId));
	},

	async getTrustScore(merchantId) {
		return mockAdapter.getTrustScore(normalizeMerchantId(merchantId));
	},

	async getInvoices(merchantId) {
		return mockAdapter.getInvoices(normalizeMerchantId(merchantId));
	},

	async requestCreditOffer(merchantId, invoiceId) {
		return mockAdapter.requestCreditOffer(normalizeMerchantId(merchantId), invoiceId);
	},

	async acceptCreditOffer(merchantId, offerId) {
		return mockAdapter.acceptCreditOffer(normalizeMerchantId(merchantId), offerId);
	},

	async getNotifications(merchantId) {
		return mockAdapter.getNotifications(normalizeMerchantId(merchantId));
	},

	async getAuditLog(merchantId) {
		return mockAdapter.getAuditLog(normalizeMerchantId(merchantId));
	},

	async getMerchantProfile(merchantId) {
		return mockAdapter.getMerchantProfile(normalizeMerchantId(merchantId));
	},

	async resetDemo() {
		return mockAdapter.resetDemo();
	},

	async sendWhatsappAlert(input) {
		return mockAdapter.sendWhatsappAlert({
			...input,
			merchantId: DEMO_MERCHANT_ID,
		});
	},

	async getMerchants() {
		const profile = await mockAdapter.getMerchantProfile(DEMO_MERCHANT_ID);
		return [profile];
	},

	async loginWithPin(_merchantId, pinHash) {
		return mockAdapter.loginWithPin(DEMO_MERCHANT_ID, pinHash);
	},

	async registerAccount() {
		throw new Error("Demo mode only: account registration is disabled");
	},

	async markNotificationRead(_merchantId, notifId) {
		return mockAdapter.markNotificationRead(DEMO_MERCHANT_ID, notifId);
	},

	async markAllNotificationsRead() {
		return mockAdapter.markAllNotificationsRead(DEMO_MERCHANT_ID);
	},

	async getDashboard(merchantId) {
		const draft = await mockAdapter.getGSTDraft(normalizeMerchantId(merchantId));
		return mapDraftToDashboard(draft);
	},

	async getTransactions(merchantId) {
		const draft = await mockAdapter.getGSTDraft(normalizeMerchantId(merchantId));
		return mapDraftToTransactions(draft);
	},

	async getReviewQueue(merchantId) {
		const draft = await mockAdapter.getGSTDraft(normalizeMerchantId(merchantId));
		return mapDraftToReviewQueue(draft);
	},

	async resolveReviewItem(queueId, payload) {
		const txId = parseQueueTxId(queueId);
		await mockAdapter.updateGSTTransaction(DEMO_MERCHANT_ID, {
			txId,
			hsnCode: payload.hsnCode,
			gstRate: payload.gstRate,
		});

		const result: ResolveReviewItemResult = {
			status: payload.status === "updated" ? "updated" : "resolved",
			queueId,
			merchantId: DEMO_MERCHANT_ID,
			txId,
			updatedAt: nowIso(),
		};

		return result;
	},

	async generateGSTR1(merchantId) {
		const draft = await mockAdapter.getGSTDraft(normalizeMerchantId(merchantId));
		const result: GSTR1GenerationResult = {
			status: "completed",
			merchantId: DEMO_MERCHANT_ID,
			generatedAt: nowIso(),
			recordCount: draft.transactions.length,
		};
		return result;
	},

	async getGSTR1Draft(merchantId) {
		const draft = await mockAdapter.getGSTDraft(normalizeMerchantId(merchantId));
		return toGstr1Draft(draft);
	},

	async generateGSTR3B(merchantId) {
		const draft = await mockAdapter.getGSTDraft(normalizeMerchantId(merchantId));
		const result: GSTR3BGenerationResult = {
			status: "completed",
			merchantId: DEMO_MERCHANT_ID,
			generatedAt: nowIso(),
			recordCount: draft.transactions.length,
		};
		return result;
	},

	async getGSTR3BSummary(merchantId) {
		const draft = await mockAdapter.getGSTDraft(normalizeMerchantId(merchantId));
		return toGstr3bSummary(draft);
	},

	async scanBill(file) {
		if (!liveAdapter.scanBill) {
			throw new Error("Bill scanner endpoint is unavailable");
		}
		return liveAdapter.scanBill(file);
	},

	async saveOcrResult(merchantId, structuredJson) {
		if (!liveAdapter.saveOcrResult) {
			throw new Error("OCR save endpoint is unavailable");
		}
		return liveAdapter.saveOcrResult(normalizeMerchantId(merchantId), structuredJson);
	},

	async sendGstVoiceAudio(audioBlob, filename) {
		if (!liveAdapter.sendGstVoiceAudio) {
			throw new Error("Voice audio endpoint is unavailable");
		}
		return liveAdapter.sendGstVoiceAudio(audioBlob, filename);
	},

	async sendGstVoiceText(query: string) {
		if (!liveAdapter.sendGstVoiceText) {
			throw new Error("Voice text endpoint is unavailable");
		}
		return liveAdapter.sendGstVoiceText(query);
	},
};

export const adapter = FORCE_SINGLE_DEMO_MERCHANT ? demoAdapter : selectedAdapter;
export const adapterMode = FORCE_SINGLE_DEMO_MERCHANT ? "mock" : mode === "live" ? "live" : "mock";
export const hardcodedDemoMerchantId = DEMO_MERCHANT_ID;
