import { Bell, FileText, FolderSearch, ReceiptIndianRupee, SendHorizonal } from 'lucide-react';
import { Button } from '@/components/ui/button';

export type EmptyIcon = 'invoice' | 'gst' | 'notification' | 'audit' | 'transfer' | 'generic';

interface EmptyAction {
  label: string;
  onClick: () => void;
}

interface EmptyStateProps {
  icon?: EmptyIcon;
  title: string;
  description: string;
  action?: EmptyAction;
}

function iconFor(type: EmptyIcon) {
  const className = 'h-16 w-16 text-slate-400';
  if (type === 'invoice') {
    return <ReceiptIndianRupee className={className} strokeWidth={1.5} />;
  }
  if (type === 'gst') {
    return <FileText className={className} strokeWidth={1.5} />;
  }
  if (type === 'notification') {
    return <Bell className={className} strokeWidth={1.5} />;
  }
  if (type === 'audit') {
    return <FolderSearch className={className} strokeWidth={1.5} />;
  }
  if (type === 'transfer') {
    return <SendHorizonal className={className} strokeWidth={1.5} />;
  }
  return <FileText className={className} strokeWidth={1.5} />;
}

export function EmptyState({ icon = 'generic', title, description, action }: EmptyStateProps) {
  return (
    <div className="paytm-surface flex flex-col items-center px-6 py-12 text-center">
      {iconFor(icon)}
      <h3 className="mt-4 text-base font-semibold text-[#002970]">{title}</h3>
      <p className="mt-2 max-w-lg text-sm text-slate-500">{description}</p>
      {action ? (
        <Button variant="outline" onClick={action.onClick} className="mt-5 rounded-full border-[#002970] text-[#002970]">
          {action.label}
        </Button>
      ) : null}
    </div>
  );
}
