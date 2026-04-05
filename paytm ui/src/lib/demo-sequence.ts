export interface DemoSequenceStep {
  id: string;
  label: string;
  route: string;
  pauseMs: number;
  narration: string;
}

export const DEMO_SEQUENCE_STEPS: DemoSequenceStep[] = [
  {
    id: "overview",
    label: "Dashboard overview",
    route: "/merchant/dashboard",
    pauseMs: 3000,
    narration: "Dashboard snapshot: wallet, trust score, GST and invoices in one view.",
  },
  {
    id: "gst-review",
    label: "GST review",
    route: "/merchant/gst/review",
    pauseMs: 3000,
    narration: "Review flagged transactions before filing.",
  },
  {
    id: "gst-file",
    label: "GST filed",
    route: "/merchant/gst/review",
    pauseMs: 3000,
    narration: "GST filing complete. Compliance moves trust upward.",
  },
  {
    id: "invoices",
    label: "Invoice financing",
    route: "/merchant/invoices",
    pauseMs: 3000,
    narration: "Overdue invoice unlocks an instant advance offer.",
  },
  {
    id: "audit",
    label: "Audit proof chain",
    route: "/merchant/audit",
    pauseMs: 3000,
    narration: "Full proof chain visible in the audit trail.",
  },
];

export async function playDemoSequence(
  onStep: (step: DemoSequenceStep) => Promise<void> | void,
): Promise<void> {
  for (const step of DEMO_SEQUENCE_STEPS) {
    await onStep(step);
    await new Promise((resolve) => setTimeout(resolve, step.pauseMs));
  }
}
