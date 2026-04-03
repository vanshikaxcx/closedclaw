// Mock user database for demo purposes
export const mockUsers = [
  {
    email: 'demo@paytm.com',
    phone: '9876543210',
    password: 'password123', // In real app, this would be hashed
    name: 'Demo User',
  },
  {
    email: 'user@paytm.com',
    phone: '9123456789',
    password: 'demo123',
    name: 'Paytm User',
  },
];

// Validate credentials (demo only - never do this in production)
export function validateCredentials(emailOrPhone: string, password: string) {
  return mockUsers.some(
    user =>
      (user.email === emailOrPhone || user.phone === emailOrPhone) &&
      user.password === password
  );
}

export function getUserData(emailOrPhone: string) {
  return mockUsers.find(
    user =>
      user.email === emailOrPhone || user.phone === emailOrPhone
  );
}
