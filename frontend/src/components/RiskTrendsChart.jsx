// RiskTrendsChart.jsx - Historical risk trend visualization
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Calendar, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend,
  Line,
  ComposedChart,
  Bar
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-zinc-800 border border-white/10 rounded-lg px-3 py-2 shadow-xl">
        <p className="text-sm font-medium text-white mb-2">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-xs flex items-center gap-2" style={{ color: entry.color }}>
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
            {entry.name}: {entry.value}
            {entry.dataKey === 'overall_score' && '%'}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const periodOptions = [
  { label: '7 days', value: 7 },
  { label: '14 days', value: 14 },
  { label: '30 days', value: 30 },
];

export default function RiskTrendsChart({ trends = [], loading = false, onPeriodChange }) {
  const [period, setPeriod] = useState(14);

  const handlePeriodChange = (days) => {
    setPeriod(days);
    if (onPeriodChange) {
      onPeriodChange(days);
    }
  };

  if (loading) {
    return (
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <TrendingUp className="w-5 h-5 text-blue-500" />
            Risk Trends
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-zinc-800/50 rounded-lg animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  // Calculate trend direction
  const getTrendDirection = () => {
    if (trends.length < 2) return 'neutral';
    const recent = trends.slice(-3);
    const older = trends.slice(-6, -3);
    
    const recentAvg = recent.reduce((a, b) => a + (b.overall_score || 0), 0) / recent.length;
    const olderAvg = older.length > 0 
      ? older.reduce((a, b) => a + (b.overall_score || 0), 0) / older.length 
      : recentAvg;
    
    if (recentAvg > olderAvg + 5) return 'up';
    if (recentAvg < olderAvg - 5) return 'down';
    return 'neutral';
  };

  const trendDirection = getTrendDirection();
  const latestScore = trends.length > 0 ? trends[trends.length - 1].overall_score : 0;
  const previousScore = trends.length > 1 ? trends[trends.length - 2].overall_score : latestScore;
  const scoreDelta = latestScore - previousScore;

  return (
    <Card className="bg-zinc-900/50 border-white/10">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-white">
            <TrendingUp className="w-5 h-5 text-blue-500" />
            Risk Trends
          </CardTitle>
          <div className="flex items-center gap-2">
            {/* Trend indicator */}
            <div className={cn(
              'flex items-center gap-1 px-2 py-1 rounded text-xs font-medium',
              trendDirection === 'up' && 'bg-red-500/20 text-red-400',
              trendDirection === 'down' && 'bg-green-500/20 text-green-400',
              trendDirection === 'neutral' && 'bg-zinc-500/20 text-zinc-400'
            )}>
              {trendDirection === 'up' && <TrendingUp className="w-3 h-3" />}
              {trendDirection === 'down' && <TrendingDown className="w-3 h-3" />}
              {trendDirection === 'neutral' && <Minus className="w-3 h-3" />}
              {trendDirection === 'up' && 'Increasing'}
              {trendDirection === 'down' && 'Improving'}
              {trendDirection === 'neutral' && 'Stable'}
            </div>
            
            {/* Period selector */}
            <div className="flex items-center gap-1 bg-zinc-800 rounded-lg p-0.5">
              {periodOptions.map(opt => (
                <Button
                  key={opt.value}
                  variant="ghost"
                  size="sm"
                  className={cn(
                    'h-7 px-2 text-xs',
                    period === opt.value 
                      ? 'bg-zinc-700 text-white' 
                      : 'text-zinc-400 hover:text-white'
                  )}
                  onClick={() => handlePeriodChange(opt.value)}
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {trends.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-zinc-400">
            <div className="text-center">
              <Calendar className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No trend data available yet.</p>
              <p className="text-sm text-zinc-500 mt-1">Snapshots are created automatically on each sync.</p>
            </div>
          </div>
        ) : (
          <>
            {/* Current stats */}
            <div className="grid grid-cols-4 gap-4 mb-4 p-3 rounded-lg bg-zinc-800/50">
              <div className="text-center">
                <p className="text-2xl font-bold text-white">{latestScore}%</p>
                <p className="text-xs text-zinc-500">Current Risk</p>
              </div>
              <div className="text-center">
                <p className={cn(
                  'text-2xl font-bold',
                  scoreDelta > 0 ? 'text-red-400' : scoreDelta < 0 ? 'text-green-400' : 'text-zinc-400'
                )}>
                  {scoreDelta > 0 ? '+' : ''}{scoreDelta}
                </p>
                <p className="text-xs text-zinc-500">vs Yesterday</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-white">
                  {trends.length > 0 ? trends[trends.length - 1].high_risk_count || 0 : 0}
                </p>
                <p className="text-xs text-zinc-500">High Risk</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-white">
                  {trends.length > 0 ? trends[trends.length - 1].task_count || 0 : 0}
                </p>
                <p className="text-xs text-zinc-500">Total Tasks</p>
              </div>
            </div>

            {/* Chart */}
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={trends} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                  <defs>
                    <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#71717a" 
                    tick={{ fill: '#71717a', fontSize: 10 }}
                    tickLine={false}
                  />
                  <YAxis 
                    yAxisId="left"
                    stroke="#71717a" 
                    tick={{ fill: '#71717a', fontSize: 10 }}
                    tickLine={false}
                    domain={[0, 100]}
                  />
                  <YAxis 
                    yAxisId="right"
                    orientation="right"
                    stroke="#71717a" 
                    tick={{ fill: '#71717a', fontSize: 10 }}
                    tickLine={false}
                    hide
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend 
                    wrapperStyle={{ paddingTop: '10px' }}
                    iconType="line"
                  />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="overall_score"
                    name="Risk Score"
                    stroke="#3b82f6"
                    fillOpacity={1}
                    fill="url(#colorRisk)"
                    strokeWidth={2}
                  />
                  <Bar
                    yAxisId="right"
                    dataKey="high_risk_count"
                    name="High Risk Tasks"
                    fill="#ef4444"
                    opacity={0.5}
                    barSize={20}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
