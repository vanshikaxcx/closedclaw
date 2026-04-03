'use client';

import { useEffect, useMemo, useState } from 'react';
import { RadialBar, RadialBarChart, ResponsiveContainer } from 'recharts';
import type { TrustScore } from '@/src/adapters/types';

interface TrustScoreGaugeProps {
  trustScore: TrustScore;
  size?: number;
}

function bucketColor(bucket: TrustScore['bucket']): string {
  if (bucket === 'Excellent') {
    return '#22C55E';
  }
  if (bucket === 'Good') {
    return '#3B82F6';
  }
  if (bucket === 'Medium') {
    return '#F59E0B';
  }
  return '#EF4444';
}

export function TrustScoreGauge({ trustScore, size = 260 }: TrustScoreGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(trustScore.score);

  useEffect(() => {
    let frame = 0;
    const start = animatedScore;
    const end = trustScore.score;
    const totalFrames = 20;

    const id = window.setInterval(() => {
      frame += 1;
      const progress = Math.min(1, frame / totalFrames);
      const value = Math.round(start + (end - start) * progress);
      setAnimatedScore(value);

      if (progress >= 1) {
        window.clearInterval(id);
      }
    }, 24);

    return () => window.clearInterval(id);
  }, [trustScore.score]);

  const data = useMemo(
    () => [
      {
        name: 'score',
        value: animatedScore,
        fill: bucketColor(trustScore.bucket),
      },
    ],
    [animatedScore, trustScore.bucket],
  );

  const components = [
    { label: 'Payment Rate', value: trustScore.components.paymentRate, max: 30 },
    { label: 'Consistency', value: trustScore.components.consistency, max: 20 },
    { label: 'Volume Trend', value: trustScore.components.volumeTrend, max: 20 },
    { label: 'GST Compliance', value: trustScore.components.gstCompliance, max: 20 },
    { label: 'Return Rate', value: trustScore.components.returnRate, max: 10 },
  ];

  return (
    <article className="paytm-surface p-6">
      <div style={{ width: size, height: size }} className="mx-auto relative">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            data={data}
            innerRadius="70%"
            outerRadius="96%"
            startAngle={210}
            endAngle={-30}
            barSize={18}
          >
            <RadialBar dataKey="value" cornerRadius={12} background={{ fill: '#e8eef8' }} />
          </RadialBarChart>
        </ResponsiveContainer>

        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <p className="text-4xl font-black text-[#002970]">{animatedScore}</p>
          <p className="text-sm font-semibold text-slate-500">{trustScore.bucket}</p>
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {components.map((component) => {
          const width = Math.max(4, Math.min(100, (component.value / component.max) * 100));
          return (
            <div key={component.label}>
              <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
                <span>{component.label}</span>
                <span className="font-semibold">{component.value}/{component.max}</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100">
                <div className="h-2 rounded-full bg-[#00BAF2] transition-all duration-500" style={{ width: `${width}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}
