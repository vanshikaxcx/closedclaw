'use client';

import { Header } from '@/components/header';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { CreditCard, TrendingUp, Shield, Home, DollarSign, PieChart, Heart, Wallet } from 'lucide-react';

export default function PaymentsServicesPage() {
  const services = [
    {
      icon: CreditCard,
      title: 'Credit Cards',
      description: 'Apply for premium credit cards with exclusive benefits',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      icon: TrendingUp,
      title: 'Investments',
      description: 'Invest in mutual funds, stocks & gold',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      icon: Shield,
      title: 'Insurance',
      description: 'Health, life & motor insurance plans',
      color: 'text-red-600',
      bgColor: 'bg-red-50',
    },
    {
      icon: Home,
      title: 'Home Loan',
      description: 'Low interest home loans for your dream home',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      icon: DollarSign,
      title: 'Personal Loans',
      description: 'Quick loans with instant approval',
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
    {
      icon: PieChart,
      title: 'Wealth Management',
      description: 'Grow your wealth with expert guidance',
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
    },
  ];

  return (
    <>
      <Header />

      <main className="bg-gray-50 min-h-screen">
        {/* Header Section */}
        <section className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Payments & Services</h1>
            <p className="text-gray-600">Explore financial services tailored for you</p>
          </div>
        </section>

        {/* Services Grid */}
        <section className="max-w-7xl mx-auto px-4 py-12">
          <h2 className="text-2xl font-bold mb-8">Financial Services</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {services.map((service, idx) => {
              const Icon = service.icon;
              return (
                <Card key={idx} className={`p-6 ${service.bgColor} border-0 hover:shadow-lg transition cursor-pointer`}>
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-white rounded-lg">
                      <Icon size={24} className={service.color} />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-bold text-gray-900 mb-1">{service.title}</h3>
                      <p className="text-sm text-gray-600 mb-4">{service.description}</p>
                      <Button variant="link" size="sm" className="p-0 text-primary">
                        Explore →
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>

          {/* Featured - Paytm Money */}
          <div className="bg-linear-to-r from-primary to-blue-600 text-white rounded-lg p-12 mb-12">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
              <div>
                <h2 className="text-3xl font-bold mb-4">Paytm Money</h2>
                <p className="text-blue-100 mb-6">
                  Invest with confidence. Get expert-backed investment advice and grow your wealth.
                </p>
                <div className="space-y-3 mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-blue-200 rounded-full" />
                    <span className="text-sm">Mutual funds, stocks & gold</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-blue-200 rounded-full" />
                    <span className="text-sm">Zero brokerage on stocks</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-blue-200 rounded-full" />
                    <span className="text-sm">Expert guidance & portfolio tracking</span>
                  </div>
                </div>
                <Button className="bg-white text-primary hover:bg-gray-100 font-semibold">
                  Start Investing Now
                </Button>
              </div>
              <div className="text-6xl text-center">📈</div>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
            <Card className="p-6 text-center">
              <p className="text-3xl font-bold text-primary mb-2">5M+</p>
              <p className="text-gray-600">Active Users</p>
            </Card>
            <Card className="p-6 text-center">
              <p className="text-3xl font-bold text-primary mb-2">₹50,000 Cr</p>
              <p className="text-gray-600">Assets Managed</p>
            </Card>
            <Card className="p-6 text-center">
              <p className="text-3xl font-bold text-primary mb-2">24/7</p>
              <p className="text-gray-600">Customer Support</p>
            </Card>
          </div>

          {/* UPI Payments */}
          <h2 className="text-2xl font-bold mb-8">UPI Payments</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <Card className="p-8 border-primary border-2">
              <h3 className="text-xl font-bold mb-4">Instant Transfer</h3>
              <p className="text-gray-600 mb-6">Send money instantly to any bank account using UPI</p>
              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-3">
                  <Heart size={18} className="text-red-500" />
                  <span className="text-sm">24/7 instant transfer</span>
                </div>
                <div className="flex items-center gap-3">
                  <Heart size={18} className="text-red-500" />
                  <span className="text-sm">Zero transaction charges</span>
                </div>
                <div className="flex items-center gap-3">
                  <Heart size={18} className="text-red-500" />
                  <span className="text-sm">Secure & encrypted</span>
                </div>
              </div>
              <Button className="w-full bg-primary hover:bg-blue-700 text-white">
                Send Money
              </Button>
            </Card>

            <Card className="p-8">
              <h3 className="text-xl font-bold mb-4">QR Code Payment</h3>
              <p className="text-gray-600 mb-6">Scan & pay with Paytm. Perfect for shops & restaurants.</p>
              <div className="bg-gray-100 rounded-lg p-6 flex items-center justify-center mb-6">
                <div className="w-32 h-32 bg-gray-200 rounded-lg flex items-center justify-center">
                  <Wallet size={48} className="text-gray-400" />
                </div>
              </div>
              <Button variant="outline" className="w-full">
                Generate QR Code
              </Button>
            </Card>
          </div>
        </section>
      </main>
    </>
  );
}
