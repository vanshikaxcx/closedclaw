import type { Metadata } from 'next'
import { Analytics } from '@vercel/analytics/next'
import { AuthProvider } from '@/lib/auth-context'
import { ToastProvider } from '@/src/context/toast-context'
import { PINProvider } from '@/src/context/pin-context'
import './globals.css'

export const metadata: Metadata = {
  title: 'Paytm x ArthSetu Demo',
  description: 'Paytm-style frontend with embedded ArthSetu merchant and admin journeys',
  icons: {
    icon: '/favicon-paytm-upi.png',
    shortcut: '/favicon-paytm-upi.png',
    apple: '/favicon-paytm-upi.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <AuthProvider>
          <ToastProvider>
            <PINProvider>
              {children}
              <Analytics />
            </PINProvider>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
