// BurndownChart.jsx - Sprint burndown visualization
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingDown, Calendar, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend,
  ReferenceLine
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-zinc-800 border border-white/10 rounded-lg px-3 py-2 shadow-xl">
        <p className="text-sm font-medium text-white mb-1">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-xs" style={{ color: entry.color }}>
            {entry.name}: {entry.value !== null ? `${entry.value} pts` : 'N/A'}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export default function BurndownChart({ data, loading = false }) {
  if (loading) {
    return (
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <TrendingDown className="w-5 h-5 text-blue-500" />
            Sprint Burndown
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-zinc-800/50 rounded-lg animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  if (!data || !data.dates) {
    return (
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <TrendingDown className="w-5 h-5 text-blue-500" />
            Sprint Burndown
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center text-zinc-400">
            <p>No burndown data available. Sync tasks first.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const {
    dates = [],
    ideal = [],
    actual = [],
    total_points = 0,
    completed_points = 0,
    remaining_points = 0,
    velocity = 0,
    days_elapsed = 0,
    days_remaining = 0
  } = data;

  // Prepare chart data
  const chartData = dates.map((date, index) => ({
    date,
    ideal: ideal[index],
    actual: actual[index]
  }));

  // Calculate if on track
  const currentIdeal = ideal[days_elapsed] || 0;
  const currentActual = remaining_points;
  const variance = currentActual - currentIdeal;
  const isOnTrack = variance <= total_points * 0.1; // Within 10%

  return (
    <Card className="bg-zinc-900/50 border-white/10">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-white">
            <TrendingDown className="w-5 h-5 text-blue-500" />
            Sprint Burndown
          </CardTitle>
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-zinc-400" />
              <span className="text-zinc-400">{days_remaining} days left</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-yellow-400" />
              <span className="text-zinc-400">{velocity} pts/day</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Status indicator */}
        <div className={cn(
          'mb-4 p-3 rounded-lg border',
          isOnTrack 
            ? 'bg-green-500/5 border-green-500/20' 
            : 'bg-yellow-500/5 border-yellow-500/20'
        )}>
          <div className="flex items-center justify-between">
            <div>
              <p className={cn(
                'text-sm font-medium',
                isOnTrack ? 'text-green-400' : 'text-yellow-400'
              )}>
                {isOnTrack ? '✓ On Track' : '⚠ Behind Schedule'}
              </p>
              <p className="text-xs text-zinc-400 mt-0.5">
                {remaining_points} points remaining • {completed_points} completed
              </p>
            </div>
            {!isOnTrack && variance > 0 && (
              <div className="text-right">
                <p className="text-lg font-bold text-yellow-400">+{Math.round(variance)}</p>
                <p className="text-xs text-zinc-500">pts behind</p>
              </div>
            )}
          </div>
        </div>

        {/* Chart */}
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis 
                dataKey="date" 
                stroke="#71717a" 
                tick={{ fill: '#71717a', fontSize: 11 }}
                tickLine={false}
              />
              <YAxis 
                stroke="#71717a" 
                tick={{ fill: '#71717a', fontSize: 11 }}
                tickLine={false}
                domain={[0, 'auto']}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                wrapperStyle={{ paddingTop: '10px' }}
                iconType="line"
              />
              <ReferenceLine 
                x={dates[days_elapsed]} 
                stroke="#3b82f6" 
                strokeDasharray="5 5" 
                label={{ value: 'Today', fill: '#3b82f6', fontSize: 10 }}
              />
              <Line
                type="monotone"
                dataKey="ideal"
                name="Ideal"
                stroke="#6b7280"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                activeDot={{ r: 4, fill: '#6b7280' }}
              />
              <Line
                type="monotone"
                dataKey="actual"
                name="Actual"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#3b82f6' }}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
