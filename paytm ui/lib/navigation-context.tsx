'use client';

import React, { createContext, useContext, useState } from 'react';

type Page =
  | 'home'
  | 'transfer'
  | 'bills'
  | 'flights'
  | 'services'
  | 'merchant'
  | 'profile';

interface NavigationContextType {
  currentPage: Page;
  setCurrentPage: (page: Page) => void;
}

const NavigationContext = createContext<NavigationContextType | undefined>(
  undefined
);

export function NavigationProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [currentPage, setCurrentPage] = useState<Page>('home');

  return (
    <NavigationContext.Provider value={{ currentPage, setCurrentPage }}>
      {children}
    </NavigationContext.Provider>
  );
}

export function useNavigation() {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigation must be used within NavigationProvider');
  }
  return context;
}
