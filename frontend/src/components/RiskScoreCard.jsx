import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export const RiskScoreCard = ({ score, trend, label, className }) => {
  const getScoreColor = (score) => {
    if (score >= 70) return 'text-red-500';
    if (score >= 40) return 'text-amber-500';
    return 'text-emerald-500';
  };

  const getTrendIcon = () => {
    if (trend > 0) return <TrendingUp className="w-4 h-4 text-red-500" />;
    if (trend < 0) return <TrendingDown className="w-4 h-4 text-emerald-500" />;
    return <Minus className="w-4 h-4 text-zinc-500" />;
  };

  return (
    <div className={cn("p-4 rounded-lg bg-zinc-800/50 border border-white/5", className)}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-zinc-500 uppercase tracking-wider">{label}</span>
        {trend !== undefined && getTrendIcon()}
      </div>
      <div className="flex items-baseline gap-1">
        <span className={cn("text-3xl font-bold font-mono", getScoreColor(score))}>
          {score}
        </span>
        <span className="text-sm text-zinc-500">%</span>
      </div>
      {trend !== undefined && trend !== 0 && (
        <p className={cn("text-xs mt-1", trend > 0 ? "text-red-500" : "text-emerald-500")}>
          {trend > 0 ? '+' : ''}{trend}% from last assessment
        </p>
      )}
    </div>
  );
};
