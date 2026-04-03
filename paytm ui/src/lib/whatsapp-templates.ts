interface GSTFiledTemplateInput {
  refId: string;
  date: string;
  amount: number;
}

interface InvoiceAdvanceTemplateInput {
  amount: number;
  invoiceId: string;
  buyerName: string;
}

interface StockAlertTemplateInput {
  amount: number;
}

interface TransferTemplateInput {
  amount: number;
  recipientName: string;
  upiId: string;
  txId: string;
  balance: number;
}

const inr = new Intl.NumberFormat("en-IN");

export const WHATSAPP_TEMPLATES = {
  gstFiled: ({ refId, date, amount }: GSTFiledTemplateInput): string =>
    `ArthSetu Alert: Your GSTR-1 for Q1 2026 has been successfully filed. Reference: ${refId}. Filing date: ${date}. Total tax paid: Rs. ${inr.format(amount)}. Thank you for staying compliant.`,

  invoiceAdvanceAccepted: ({ amount, invoiceId, buyerName }: InvoiceAdvanceTemplateInput): string =>
    `ArthSetu Finance: Your advance of Rs. ${inr.format(amount)} against Invoice #${invoiceId} has been approved. Disbursement expected within 4 hours. Repayment will be auto-deducted when ${buyerName} pays. ArthSetu Team.`,

  stockReorderAlert: ({ amount }: StockAlertTemplateInput): string =>
    `ArthSetu CashFlow Alert: Based on last month's patterns, your stock reorder window starts in 3 days. Expected inflow this week: Rs. ${inr.format(amount)}. You're clear to reorder. - ArthSetu`,

  transferSuccess: ({ amount, recipientName, upiId, txId, balance }: TransferTemplateInput): string =>
    `ArthSetu Wallet: Rs. ${inr.format(amount)} sent to ${recipientName} (${upiId}). Transaction ID: ${txId}. Balance: Rs. ${inr.format(balance)}.`,
};

export const DEMO_WHATSAPP_PHONE = "+91-98765-43210";
