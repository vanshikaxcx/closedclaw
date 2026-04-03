'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';

interface PromoCardProps {
  title: string;
  description: string;
  bgColor: 'bg-yellow-50' | 'bg-blue-50' | 'bg-teal-50' | 'bg-green-50';
  borderColor: string;
  badgeText?: string;
  icon?: React.ReactNode;
  ctaText: string;
  ctaLink?: string;
  onCtaClick?: () => void;
}

export function PromoCard({
  title,
  description,
  bgColor,
  borderColor,
  badgeText,
  icon,
  ctaText,
  ctaLink,
  onCtaClick,
}: PromoCardProps) {
  const content = (
    <div className={`${bgColor} border ${borderColor} rounded-lg p-6 flex items-start justify-between gap-4`}>
      <div className="flex-1">
        {badgeText && (
          <div className="inline-block bg-yellow-300 text-yellow-900 text-xs font-bold px-3 py-1 rounded-full mb-2">
            {badgeText}
          </div>
        )}
        <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
        <p className="text-sm text-gray-600 mb-4">{description}</p>
        <Button
          variant="default"
          size="sm"
          className="bg-gray-900 hover:bg-gray-800"
        >
          {ctaText} →
        </Button>
      </div>
      {icon && <div className="flex-shrink-0 text-4xl">{icon}</div>}
    </div>
  );

  if (ctaLink) {
    return <Link href={ctaLink}>{content}</Link>;
  }

  return (
    <button onClick={onCtaClick} className="w-full text-left">
      {content}
    </button>
  );
}
