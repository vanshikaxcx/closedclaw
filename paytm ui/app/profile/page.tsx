'use client';

import { Header } from '@/components/header';
import { ProtectedRoute } from '@/components/protected-route';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/lib/auth-context';
import { User, LogOut, Shield, Bell, Lock } from 'lucide-react';

export default function ProfilePage() {
  const { user, logout } = useAuth();

  return (
    <ProtectedRoute>
      <Header />

      <main className="bg-gray-50 min-h-screen">
        {/* Header Section */}
        <section className="bg-white border-b">
          <div className="max-w-7xl mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">My Profile</h1>
            <p className="text-gray-600">Manage your account and preferences</p>
          </div>
        </section>

        {/* Main Content */}
        <section className="max-w-7xl mx-auto px-4 py-12">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Sidebar */}
            <div className="lg:col-span-1">
              <Card className="p-6 text-center">
                <div className="w-16 h-16 bg-primary text-white rounded-full flex items-center justify-center text-3xl mx-auto mb-4">
                  {user?.name.charAt(0)}
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-1">{user?.name}</h2>
                <p className="text-sm text-gray-600 mb-6">Account verified</p>
                <Button
                  variant="outline"
                  className="w-full flex items-center justify-center gap-2"
                  onClick={logout}
                >
                  <LogOut size={18} />
                  Sign Out
                </Button>
              </Card>

              <Card className="p-4 mt-4 bg-blue-50 border-blue-200">
                <p className="text-xs font-semibold text-blue-900 mb-2">Account Type</p>
                <p className="text-sm text-blue-900 font-medium">Personal Account</p>
              </Card>
            </div>

            {/* Main Content */}
            <div className="lg:col-span-2">
              {/* Personal Information */}
              <Card className="p-8 mb-6">
                <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                  <User size={20} />
                  Personal Information
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
                    <Input defaultValue={user?.name || ''} disabled className="bg-gray-100" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                    <div className="flex gap-2">
                      <Input
                        defaultValue={user?.email || ''}
                        disabled
                        className="bg-gray-100"
                      />
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded self-center whitespace-nowrap">
                        Verified
                      </span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Phone</label>
                    <div className="flex gap-2">
                      <Input
                        defaultValue={user?.phone || ''}
                        disabled
                        className="bg-gray-100"
                      />
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded self-center whitespace-nowrap">
                        Verified
                      </span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Account ID</label>
                    <Input defaultValue={user?.id || ''} disabled className="bg-gray-100" />
                  </div>
                </div>
              </Card>

              {/* Security Settings */}
              <Card className="p-8 mb-6">
                <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                  <Shield size={20} />
                  Security & Privacy
                </h3>

                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <Lock size={20} className="text-primary" />
                      <div>
                        <p className="font-semibold text-gray-900">Change Password</p>
                        <p className="text-xs text-gray-600">Update your password regularly</p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm">
                      Change
                    </Button>
                  </div>

                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <Shield size={20} className="text-primary" />
                      <div>
                        <p className="font-semibold text-gray-900">Two-Factor Authentication</p>
                        <p className="text-xs text-gray-600">Add an extra layer of security</p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm">
                      Enable
                    </Button>
                  </div>

                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <Lock size={20} className="text-primary" />
                      <div>
                        <p className="font-semibold text-gray-900">Active Sessions</p>
                        <p className="text-xs text-gray-600">Manage your logged in devices</p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm">
                      Manage
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Notifications */}
              <Card className="p-8 mb-6">
                <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                  <Bell size={20} />
                  Notifications
                </h3>

                <div className="space-y-4">
                  {[
                    { label: 'Transaction Alerts', description: 'Get notified on every transaction' },
                    { label: 'Promotional Offers', description: 'Receive exclusive deals and offers' },
                    { label: 'Security Updates', description: 'Important security notifications' },
                    { label: 'Email Digest', description: 'Weekly summary of your activity' },
                  ].map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-semibold text-gray-900">{item.label}</p>
                        <p className="text-xs text-gray-600">{item.description}</p>
                      </div>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" defaultChecked className="w-4 h-4" />
                      </label>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Help & Support */}
              <Card className="p-8">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Help & Support</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <button className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition text-left">
                    <p className="font-semibold text-gray-900 mb-1">Contact Support</p>
                    <p className="text-xs text-gray-600">Get help from our support team</p>
                  </button>

                  <button className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition text-left">
                    <p className="font-semibold text-gray-900 mb-1">FAQ</p>
                    <p className="text-xs text-gray-600">Browse frequently asked questions</p>
                  </button>

                  <button className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition text-left">
                    <p className="font-semibold text-gray-900 mb-1">Privacy Policy</p>
                    <p className="text-xs text-gray-600">Read our privacy policy</p>
                  </button>

                  <button className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition text-left">
                    <p className="font-semibold text-gray-900 mb-1">Terms of Service</p>
                    <p className="text-xs text-gray-600">Review terms and conditions</p>
                  </button>
                </div>
              </Card>
            </div>
          </div>
        </section>
      </main>
    </ProtectedRoute>
  );
}
