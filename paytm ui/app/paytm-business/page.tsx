'use client';

import { Header } from '@/components/header';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { TrendingUp, Users, Zap, BarChart3, Shield, Wallet } from 'lucide-react';

export default function PaytmBusinessPage() {
  const features = [
    {
      icon: Wallet,
      title: 'Payment Gateway',
      description: 'Accept payments from customers instantly',
      color: 'text-blue-600',
    },
    {
      icon: TrendingUp,
      title: 'Analytics',
      description: 'Real-time insights into your sales',
      color: 'text-green-600',
    },
    {
      icon: Users,
      title: 'Customer Management',
      description: 'Manage customers and loyalty programs',
      color: 'text-purple-600',
    },
    {
      icon: Zap,
      title: 'Instant Settlements',
      description: 'Get payments within 2 hours',
      color: 'text-orange-600',
    },
    {
      icon: Shield,
      title: 'Security',
      description: 'Bank-level security for all transactions',
      color: 'text-red-600',
    },
    {
      icon: BarChart3,
      title: 'Reports',
      description: 'Detailed business reports and exports',
      color: 'text-indigo-600',
    },
  ];

  return (
    <>
      <Header />

      <main className="bg-gray-50 min-h-screen">
        {/* Header Section */}
        <section className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Paytm for Business</h1>
            <p className="text-gray-600">Grow your business with Paytm&apos;s complete payment solutions</p>
          </div>
        </section>

        {/* Hero Section */}
        <section className="bg-linear-to-r from-primary to-blue-600 text-white">
          <div className="max-w-7xl mx-auto px-4 py-16">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
              <div>
                <h2 className="text-4xl font-bold mb-4">Accept Digital Payments</h2>
                <p className="text-blue-100 mb-6 text-lg">
                  Join millions of businesses using Paytm Payment Gateway
                </p>
                <div className="space-y-3 mb-8">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-blue-200 rounded-full" />
                    <span>0% transaction fee on UPI payments</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-blue-200 rounded-full" />
                    <span>Get payments within 2 hours</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-blue-200 rounded-full" />
                    <span>No setup fees, no hidden charges</span>
                  </div>
                </div>
                <Button className="bg-white text-primary hover:bg-gray-100 font-semibold px-8 py-3">
                  Get Started Now
                </Button>
              </div>
              <div className="text-center">
                <div className="text-8xl">💳</div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="max-w-7xl mx-auto px-4 py-16">
          <h2 className="text-3xl font-bold mb-12 text-center">Powerful Features for Your Business</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, idx) => {
              const Icon = feature.icon;
              return (
                <Card key={idx} className="p-6 hover:shadow-lg transition">
                  <div className="mb-4">
                    <Icon size={32} className={feature.color} />
                  </div>
                  <h3 className="font-bold text-gray-900 mb-2">{feature.title}</h3>
                  <p className="text-sm text-gray-600">{feature.description}</p>
                </Card>
              );
            })}
          </div>
        </section>

        {/* Pricing Section */}
        <section className="max-w-7xl mx-auto bg-white px-4 py-16">
          <h2 className="text-3xl font-bold mb-12 text-center">Simple, Transparent Pricing</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            <Card className="p-8 text-center border-gray-200">
              <h3 className="text-lg font-bold mb-2">UPI Payments</h3>
              <p className="text-4xl font-bold text-primary mb-4">0%</p>
              <p className="text-sm text-gray-600 mb-6">Transaction fee</p>
              <ul className="text-sm text-gray-600 space-y-2 text-left mb-6">
                <li>✓ Zero hidden charges</li>
                <li>✓ Instant notification</li>
                <li>✓ Settlement in 2 hours</li>
              </ul>
              <Button variant="outline">Learn More</Button>
            </Card>

            <Card className="p-8 text-center border-primary border-2 bg-blue-50">
              <div className="bg-primary text-white text-xs font-bold px-3 py-1 rounded-full inline-block mb-4">
                MOST POPULAR
              </div>
              <h3 className="text-lg font-bold mb-2">Cards & Wallets</h3>
              <p className="text-4xl font-bold text-primary mb-4">1.99%</p>
              <p className="text-sm text-gray-600 mb-6">Transaction fee</p>
              <ul className="text-sm text-gray-600 space-y-2 text-left mb-6">
                <li>✓ All payment methods</li>
                <li>✓ Fraud protection</li>
                <li>✓ 24/7 support</li>
              </ul>
              <Button className="w-full bg-primary hover:bg-blue-700 text-white">
                Get Started
              </Button>
            </Card>

            <Card className="p-8 text-center border-gray-200">
              <h3 className="text-lg font-bold mb-2">Enterprise</h3>
              <p className="text-4xl font-bold text-primary mb-4">Custom</p>
              <p className="text-sm text-gray-600 mb-6">Negotiable rates</p>
              <ul className="text-sm text-gray-600 space-y-2 text-left mb-6">
                <li>✓ Dedicated support</li>
                <li>✓ Custom integration</li>
                <li>✓ Priority settlement</li>
              </ul>
              <Button variant="outline">Contact Sales</Button>
            </Card>
          </div>
        </section>

        {/* Statistics */}
        <section className="max-w-7xl mx-auto px-4 py-16">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card className="p-6 text-center">
              <p className="text-3xl font-bold text-primary mb-2">50L+</p>
              <p className="text-gray-600">Active Merchants</p>
            </Card>
            <Card className="p-6 text-center">
              <p className="text-3xl font-bold text-primary mb-2">₹5L Cr</p>
              <p className="text-gray-600">Monthly Payment Volume</p>
            </Card>
            <Card className="p-6 text-center">
              <p className="text-3xl font-bold text-primary mb-2">99.9%</p>
              <p className="text-gray-600">Uptime Guarantee</p>
            </Card>
            <Card className="p-6 text-center">
              <p className="text-3xl font-bold text-primary mb-2">2 Hours</p>
              <p className="text-gray-600">Settlement Time</p>
            </Card>
          </div>
        </section>

        {/* CTA Section */}
        <section className="bg-primary text-white py-16">
          <div className="max-w-7xl mx-auto px-4 text-center">
            <h2 className="text-3xl font-bold mb-4">Ready to Grow Your Business?</h2>
            <p className="text-blue-100 mb-8 text-lg max-w-2xl mx-auto">
              Join thousands of successful merchants who are already accepting digital payments with Paytm
            </p>
            <Button className="bg-white text-primary hover:bg-gray-100 font-semibold px-8 py-3">
              Apply Now - It&apos;s Free
            </Button>
          </div>
        </section>
      </main>
    </>
  );
}
