'use client';

import { useState } from 'react';
import { Header } from '@/components/header';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Smartphone, Wifi, Car, Zap, Phone, Droplets } from 'lucide-react';

export default function RechargeBillsPage() {
  const [activeTab, setActiveTab] = useState<string>('mobile');

  const categories = [
    { id: 'mobile', label: 'Mobile Recharge', icon: Smartphone, color: 'text-blue-600' },
    { id: 'dth', label: 'DTH Recharge', icon: Wifi, color: 'text-purple-600' },
    { id: 'fastag', label: 'FasTag Recharge', icon: Car, color: 'text-orange-600' },
    { id: 'electricity', label: 'Electricity Bill', icon: Zap, color: 'text-yellow-600' },
    { id: 'water', label: 'Water Bill', icon: Droplets, color: 'text-cyan-600' },
    { id: 'broadband', label: 'Broadband Bill', icon: Phone, color: 'text-green-600' },
  ];

  const providers: Record<string, string[]> = {
    mobile: ['Jio', 'Airtel', 'Vodafone-Idea', 'BSNL', 'Reliance'],
    dth: ['Tata Sky', 'Airtel DTH', 'Sun Direct', 'Videocon', 'DishTV'],
    fastag: ['Jio', 'Airtel', 'ICICI Bank', 'HDFC Bank', 'AXIS Bank'],
    electricity: ['Delhi Electricity', 'Mumbai Electricity', 'Bangalore Electricity', 'Chennai Electricity'],
    water: ['Delhi Jal', 'Mumbai Water', 'Bangalore Water', 'Chennai Water'],
    broadband: ['ACT Fibernet', 'Airtel Broadband', 'Jio Fiber', 'BSNL Broadband'],
  };

  return (
    <>
      <Header />

      <main className="bg-gray-50 min-h-screen">
        {/* Header Section */}
        <section className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Recharges & Bill Payments</h1>
            <p className="text-gray-600">Pay your bills and recharge in seconds</p>
          </div>
        </section>

        {/* Category Navigation */}
        <section className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <div className="flex gap-2 overflow-x-auto pb-2 -mb-2">
              {categories.map((cat) => {
                const Icon = cat.icon;
                return (
                  <button
                    key={cat.id}
                    onClick={() => setActiveTab(cat.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap transition ${
                      activeTab === cat.id
                        ? 'bg-primary text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    <Icon size={18} />
                    <span className="text-sm font-medium">{cat.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        {/* Main Content */}
        <section className="max-w-7xl mx-auto px-4 py-12">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Form */}
            <div className="lg:col-span-2">
              <Card className="p-8">
                <h2 className="text-2xl font-bold mb-6">
                  {categories.find((c) => c.id === activeTab)?.label}
                </h2>

                <form className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Provider
                    </label>
                    <select className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent">
                      <option>Select a provider</option>
                      {providers[activeTab]?.map((provider) => (
                        <option key={provider} value={provider}>
                          {provider}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Phone/Reference Number
                    </label>
                    <Input
                      type="tel"
                      placeholder="Enter 10-digit number"
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Amount
                    </label>
                    <Input
                      type="number"
                      placeholder="Enter amount"
                      className="w-full"
                    />
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm text-blue-900">
                      <span className="font-semibold">Pro Tip:</span> Set recurring payments to auto-recharge every month
                    </p>
                  </div>

                  <Button className="w-full bg-primary hover:bg-blue-700 text-white font-medium py-3">
                    Proceed to Pay
                  </Button>
                </form>
              </Card>
            </div>

            {/* Sidebar - Offers */}
            <div>
              <Card className="p-6 mb-6 bg-linear-to-br from-yellow-50 to-yellow-100 border-yellow-200">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <span>🎉</span> Special Offers
                </h3>
                <div className="space-y-3">
                  <div>
                    <p className="font-semibold text-sm text-gray-900">₹100 Cashback</p>
                    <p className="text-xs text-gray-600">On Mobile Recharge above ₹300</p>
                  </div>
                  <div>
                    <p className="font-semibold text-sm text-gray-900">Flat 5% Off</p>
                    <p className="text-xs text-gray-600">On Broadband Bills</p>
                  </div>
                  <div>
                    <p className="font-semibold text-sm text-gray-900">₹50 Reward Points</p>
                    <p className="text-xs text-gray-600">Every recharge</p>
                  </div>
                </div>
              </Card>

              <Card className="p-6 bg-blue-50 border-blue-200">
                <h3 className="font-bold text-gray-900 mb-4">Quick Payment</h3>
                <p className="text-sm text-gray-600 mb-4">Save up to 3 frequent billers for quick access</p>
                <Button variant="outline" className="w-full text-primary border-primary hover:bg-blue-50">
                  Add Saved Biller
                </Button>
              </Card>
            </div>
          </div>

          {/* Recent Payments */}
          <div className="mt-12">
            <h3 className="text-2xl font-bold mb-6">Recent Payments</h3>
            <Card>
              <div className="divide-y">
                {[
                  { provider: 'Jio', amount: '₹299', date: 'Today at 2:45 PM', status: 'Success' },
                  { provider: 'Airtel', amount: '₹449', date: 'Yesterday', status: 'Success' },
                  { provider: 'BSNL', amount: '₹150', date: '2 days ago', status: 'Success' },
                ].map((payment, idx) => (
                  <div key={idx} className="flex items-center justify-between p-4 hover:bg-gray-50">
                    <div>
                      <p className="font-semibold text-gray-900">{payment.provider}</p>
                      <p className="text-xs text-gray-600">{payment.date}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-gray-900">{payment.amount}</p>
                      <p className="text-xs text-green-600 font-medium">{payment.status}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </section>
      </main>
    </>
  );
}
