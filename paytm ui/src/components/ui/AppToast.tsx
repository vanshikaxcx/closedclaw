import { useToast } from '@/src/context/toast-context';

type AppToastVariant = 'success' | 'error' | 'warning' | 'info' | 'whatsapp';

interface AppToastPayload {
  title: string;
  description?: string;
  variant?: AppToastVariant;
  phone?: string;
}

export function useAppToast() {
  const toast = useToast();

  function showToast({ title, description, variant = 'info', phone }: AppToastPayload): void {
    const message = description ? `${title}: ${description}` : title;

    if (variant === 'success') {
      toast.success(message);
      return;
    }
    if (variant === 'error') {
      toast.error(message);
      return;
    }
    if (variant === 'warning') {
      toast.warning(message);
      return;
    }
    if (variant === 'whatsapp' && phone) {
      toast.whatsapp(message, phone);
      return;
    }

    toast.success(message);
  }

  return {
    showToast,
  };
}
