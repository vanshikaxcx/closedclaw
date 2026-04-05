'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export function LoginForm() {
  const [emailOrPhone, setEmailOrPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(emailOrPhone, password);
      router.push('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="emailOrPhone" className="block text-sm font-medium text-gray-700 mb-2">
          Email or Phone Number
        </label>
        <Input
          id="emailOrPhone"
          type="text"
          placeholder="Enter email or phone number"
          value={emailOrPhone}
          onChange={(e) => setEmailOrPhone(e.target.value)}
          required
          className="w-full"
        />
        <p className="text-xs text-gray-500 mt-2">Try: demo@paytm.com or 9876543210</p>
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
          Password
        </label>
        <Input
          id="password"
          type="password"
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full"
        />
        <p className="text-xs text-gray-500 mt-2">Try: password123</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}

      <Button
        type="submit"
        disabled={isLoading}
        className="w-full bg-primary hover:bg-blue-700 text-white font-medium py-2.5"
      >
        {isLoading ? 'Signing in...' : 'Sign In'}
      </Button>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-300" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-white text-gray-500">Don&apos;t have an account?</span>
        </div>
      </div>

      <Link href="/auth/signup">
        <Button
          type="button"
          variant="outline"
          className="w-full"
        >
          Create Account
        </Button>
      </Link>

      <Link href="/auth/forgot-password" className="text-center text-sm text-primary hover:text-blue-700">
        Forgot Password?
      </Link>
    </form>
  );
}
