'use client';

import { useState } from 'react';
import { Header } from '@/components/header';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Plane, Bus, Train, Globe, MapPin, Calendar, Users } from 'lucide-react';

export default function TicketBookingPage() {
  const [activeTab, setActiveTab] = useState<string>('flights');
  const [tripType, setTripType] = useState<'oneWay' | 'roundTrip'>('oneWay');

  const tabs = [
    { id: 'flights', label: 'Flights', icon: Plane },
    { id: 'bus', label: 'Bus', icon: Bus },
    { id: 'trains', label: 'Trains', icon: Train },
    { id: 'intl', label: 'Intl. Flights', icon: Globe },
  ];

  const flightResults = [
    {
      airline: 'Air India',
      departure: '06:00',
      arrival: '10:30',
      duration: '4h 30m',
      stops: 'Non-stop',
      price: '₹5,299',
      seats: 245,
    },
    {
      airline: 'IndiGo',
      departure: '09:15',
      arrival: '13:45',
      duration: '4h 30m',
      stops: 'Non-stop',
      price: '₹4,899',
      seats: 120,
    },
    {
      airline: 'SpiceJet',
      departure: '14:00',
      arrival: '18:30',
      duration: '4h 30m',
      stops: 'Non-stop',
      price: '₹4,599',
      seats: 89,
    },
  ];

  return (
    <>
      <Header />

      <main className="bg-gray-50 min-h-screen">
        {/* Header Section */}
        <section className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Book Flights, Buses & Trains</h1>
            <p className="text-gray-600">Find and book your tickets in seconds</p>
          </div>
        </section>

        {/* Tab Navigation */}
        <section className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex gap-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-4 py-4 border-b-2 transition ${
                      activeTab === tab.id
                        ? 'border-primary text-primary'
                        : 'border-transparent text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <Icon size={18} />
                    <span className="font-medium">{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        {/* Search Section */}
        <section className="max-w-7xl mx-auto px-4 py-12">
          <Card className="p-8 mb-8">
            {/* Trip Type */}
            <div className="mb-6">
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={tripType === 'oneWay'}
                    onChange={() => setTripType('oneWay')}
                    className="w-4 h-4"
                  />
                  <span className="text-sm font-medium">One Way</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={tripType === 'roundTrip'}
                    onChange={() => setTripType('roundTrip')}
                    className="w-4 h-4"
                  />
                  <span className="text-sm font-medium">Round Trip</span>
                </label>
              </div>
            </div>

            {/* Search Form */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">From</label>
                <div className="relative">
                  <MapPin size={18} className="absolute left-3 top-3 text-gray-400" />
                  <Input placeholder="Departure city" className="pl-10" />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">To</label>
                <div className="relative">
                  <MapPin size={18} className="absolute left-3 top-3 text-gray-400" />
                  <Input placeholder="Arrival city" className="pl-10" />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Departure</label>
                <div className="relative">
                  <Calendar size={18} className="absolute left-3 top-3 text-gray-400" />
                  <Input type="date" className="pl-10" />
                </div>
              </div>

              {tripType === 'roundTrip' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Return</label>
                  <div className="relative">
                    <Calendar size={18} className="absolute left-3 top-3 text-gray-400" />
                    <Input type="date" className="pl-10" />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Passengers</label>
                <div className="relative">
                  <Users size={18} className="absolute left-3 top-3 text-gray-400" />
                  <Input type="number" defaultValue="1" className="pl-10" />
                </div>
              </div>
            </div>

            <Button className="w-full bg-primary hover:bg-blue-700 text-white font-medium py-3">
              Search {activeTab === 'flights' || activeTab === 'intl' ? 'Flights' : activeTab === 'bus' ? 'Buses' : 'Trains'}
            </Button>
          </Card>

          {/* Results */}
          {activeTab === 'flights' || activeTab === 'intl' ? (
            <div>
              <h2 className="text-2xl font-bold mb-6">
                {flightResults.length} Flights Found
              </h2>
              <div className="space-y-4">
                {flightResults.map((flight, idx) => (
                  <Card key={idx} className="p-6 hover:shadow-lg transition">
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-6 items-center">
                      <div>
                        <p className="font-bold text-gray-900 mb-1">{flight.airline}</p>
                        <p className="text-xs text-gray-600">{flight.seats} seats available</p>
                      </div>

                      <div className="text-center">
                        <p className="text-lg font-bold text-gray-900">{flight.departure}</p>
                        <p className="text-xs text-gray-600">Departure</p>
                      </div>

                      <div className="text-center">
                        <p className="text-xs text-gray-600 mb-1">{flight.duration}</p>
                        <p className="text-xs font-medium text-primary">{flight.stops}</p>
                      </div>

                      <div className="text-center">
                        <p className="text-lg font-bold text-gray-900">{flight.arrival}</p>
                        <p className="text-xs text-gray-600">Arrival</p>
                      </div>

                      <div className="flex flex-col items-end gap-2">
                        <div className="text-right">
                          <p className="text-2xl font-bold text-primary">{flight.price}</p>
                          <p className="text-xs text-gray-600">per person</p>
                        </div>
                        <Button className="bg-primary hover:bg-blue-700 text-white">
                          Select
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          ) : (
            <Card className="p-12 text-center">
              <div className="text-6xl mb-4">🚌</div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">
                {activeTab === 'bus' ? 'Bus Bookings' : 'Train Bookings'} Coming Soon
              </h3>
              <p className="text-gray-600">
                {activeTab === 'bus'
                  ? 'Book buses across India with exclusive discounts'
                  : 'Book train tickets with instant confirmation'}
              </p>
            </Card>
          )}
        </section>

        {/* Offers */}
        <section className="max-w-7xl mx-auto px-4 py-12">
          <h2 className="text-2xl font-bold mb-6">Special Offers</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="p-6 bg-linear-to-br from-yellow-50 to-yellow-100 border-yellow-200">
              <p className="font-bold text-gray-900 mb-2">₹500 Off</p>
              <p className="text-sm text-gray-600 mb-4">On flight bookings above ₹5000</p>
              <Button variant="link" size="sm" className="p-0">View Deals →</Button>
            </Card>

            <Card className="p-6 bg-linear-to-br from-blue-50 to-blue-100 border-blue-200">
              <p className="font-bold text-gray-900 mb-2">Paytm Wallet Cashback</p>
              <p className="text-sm text-gray-600 mb-4">Get 5% cashback on all bookings</p>
              <Button variant="link" size="sm" className="p-0">View Deals →</Button>
            </Card>

            <Card className="p-6 bg-linear-to-br from-green-50 to-green-100 border-green-200">
              <p className="font-bold text-gray-900 mb-2">Referral Rewards</p>
              <p className="text-sm text-gray-600 mb-4">₹500 for each friend you refer</p>
              <Button variant="link" size="sm" className="p-0">View Deals →</Button>
            </Card>
          </div>
        </section>
      </main>
    </>
  );
}
