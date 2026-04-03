'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { ChevronDown, Download, LogOut, UserCircle2 } from 'lucide-react';

export function Header() {
  const { user, logout, isAuthenticated, session, isBootstrapping } = useAuth();
  const router = useRouter();
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  const menuItems = [
    { label: 'Recharge & Bills', href: '/recharge-bills' },
    { label: 'Ticket Booking', href: '/ticket-booking' },
    { label: 'Payments & Services', href: '/payments-services' },
    { label: 'Paytm for Business', href: '/paytm-business' },
    { label: 'Company', href: '/services' },
  ];

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const dashboardHref = session?.role === 'admin' ? '/admin/dashboard' : '/merchant/dashboard';

  const displayName = user?.name?.split(' ')[0] || 'User';

  const ProfileChip = (
    <button className="inline-flex items-center gap-2 rounded-full bg-[#052e72] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[#083f9f]">
      <UserCircle2 size={18} />
      {displayName}
    </button>
  );

  const SignInChip = (
    <Link
      href="/login"
      className="inline-flex items-center gap-2 rounded-full bg-[#052e72] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#083f9f]"
    >
      <UserCircle2 size={18} />
      Sign In
    </Link>
  );

  const navTextClass = 'inline-flex items-center gap-1 rounded-md px-2 py-1 text-[15px] font-semibold text-slate-800 transition hover:text-[#0a58d8]';

  const menuClass = 'absolute left-0 z-40 mt-2 w-52 rounded-xl border border-[#dbe1ec] bg-white p-2 shadow-xl';

  const renderSubmenu = (href: string) => {
    if (href === '/recharge-bills') {
      return [
        { label: 'Mobile Recharge', href: '/recharge-bills#mobile' },
        { label: 'DTH Recharge', href: '/recharge-bills#dth' },
        { label: 'FasTag Recharge', href: '/recharge-bills#fastag' },
        { label: 'Electricity Bill', href: '/recharge-bills#electricity' },
      ];
    }
    if (href === '/ticket-booking') {
      return [
        { label: 'Flights', href: '/ticket-booking#flights' },
        { label: 'Bus', href: '/ticket-booking#bus' },
        { label: 'Trains', href: '/ticket-booking#trains' },
      ];
    }
    if (href === '/payments-services') {
      return [
        { label: 'UPI Transfers', href: '/transfer' },
        { label: 'Financial Services', href: '/services' },
        { label: 'Bills', href: '/bills' },
      ];
    }
    if (href === '/paytm-business') {
      return [
        { label: 'Merchant Demo Login', href: '/login?demo=true' },
        { label: 'Merchant Dashboard', href: '/merchant/dashboard' },
        { label: 'Bill Scanner', href: '/merchant/bill-scanner' },
        { label: 'Tax Assistant', href: '/merchant/tax-assistant' },
        { label: 'Admin Dashboard', href: '/admin/dashboard' },
      ];
    }
    return [
      { label: 'Investor Relations', href: '/services' },
      { label: 'Careers', href: '/services' },
      { label: 'Resources', href: '/services' },
    ];
  };

  const showAccountMenu = isHydrated && !isBootstrapping && isAuthenticated && !!user;

  return (
    <header className="sticky top-0 z-50 border-b border-[#dce2ec] bg-white/95 backdrop-blur">
      <div className="container-paytm flex items-center justify-between gap-4 py-3">
        <Link href="/" className="flex items-center gap-2 text-[30px] leading-none font-black tracking-tight">
          <span className="text-[#0a58d8]">pay</span>
          <span className="text-[#042f72]">tm</span>
          <span className="text-[18px]">❤️</span>
          <span className="text-sm font-bold text-slate-600">UPI</span>
        </Link>

        <nav className="hidden items-center gap-1 xl:flex">
          {menuItems.map((item) => (
            <div key={item.label} className="group relative">
              <Link href={item.href} className={navTextClass}>
                {item.label}
                <ChevronDown size={16} />
              </Link>
              <div className="invisible absolute left-0 opacity-0 transition group-hover:visible group-hover:opacity-100">
                <div className={menuClass}>
                  {renderSubmenu(item.href).map((subitem) => (
                    <Link key={subitem.label} href={subitem.href} className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-[#eff4fb] hover:text-[#0a58d8]">
                      {subitem.label}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" className="hidden items-center gap-2 text-[#0a58d8] md:flex">
            <Download size={16} />
            Download App
          </Button>

          {showAccountMenu ? (
            <div className="group relative">
              {ProfileChip}
              <div className="invisible absolute right-0 opacity-0 transition group-hover:visible group-hover:opacity-100">
                <div className="mt-2 w-56 rounded-xl border border-[#dbe1ec] bg-white p-2 shadow-xl">
                  <Link href={dashboardHref} className="block rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-[#eff4fb] hover:text-[#0a58d8]">
                    Open Dashboard
                  </Link>
                  <Link href="/profile" className="block rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-[#eff4fb] hover:text-[#0a58d8]">
                    Profile
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-red-50 hover:text-red-600"
                  >
                    <LogOut size={16} />
                    Sign Out
                  </button>
                </div>
              </div>
            </div>
          ) : (
            SignInChip
          )}
        </div>
      </div>
    </header>
  );
}
