import { redirect } from 'next/navigation';

export default function MerchantGSTRootRedirect() {
  redirect('/merchant/gst/overview');
}
