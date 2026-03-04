// SprintProgressCard.jsx - Shows sprint metrics and progress
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { 
  Target, 
  CheckCircle2, 
  Clock, 
  AlertTriangle,
  TrendingUp,
  Users
} from 'lucide-react';
import { cn } from '@/lib/utils';

const MetricCard = ({ icon: Icon, label, value, subValue, color = 'blue' }) => {
  const colors = {
    blue: 'text-blue-400 bg-blue-500/10',
    green: 'text-green-400 bg-green-500/10',
    yellow: 'text-yellow-400 bg-yellow-500/10',
    red: 'text-red-400 bg-red-500/10',
    purple: 'text-purple-400 bg-purple-500/10',
  };

  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-zinc-800/50">
      <div className={cn('p-2 rounded-lg', colors[color])}>
        <Icon className={cn('w-4 h-4', colors[color].split(' ')[0])} />
      </div>
      <div>
        <p className="text-xl font-bold text-white">{value}</p>
        <p className="text-xs text-zinc-400">{label}</p>
        {subValue && <p className="text-xs text-zinc-500">{subValue}</p>}
      </div>
    </div>
  );
};

const WarningBadge = ({ count, label, color }) => {
  if (!count || count === 0) return null;
  
  const colors = {
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  };

  return (
    <Badge variant="outline" className={cn('text-xs', colors[color])}>
      {count} {label}
    </Badge>
  );
};

export default function SprintProgressCard({ data, loading = false }) {
  if (loading) {
    return (
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <Target className="w-5 h-5 text-blue-500" />
            Sprint Progress
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-32 bg-zinc-800/50 rounded-lg animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  const {
    total_tasks = 0,
    completed_tasks = 0,
    in_progress_tasks = 0,
    total_points = 0,
    completed_points = 0,
    remaining_points = 0,
    blocked_tasks = 0,
    overdue_tasks = 0,
    unassigned_tasks = 0,
    completion_percentage = 0,
    overall_risk_level = 'LOW'
  } = data || {};

  const getRiskColor = (level) => {
    switch (level) {
      case 'HIGH': return 'text-red-400';
      case 'MEDIUM': return 'text-yellow-400';
      default: return 'text-green-400';
    }
  };

  const getProgressColor = (pct) => {
    if (pct >= 70) return 'bg-green-500';
    if (pct >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <Card className="bg-zinc-900/50 border-white/10">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-white">
            <Target className="w-5 h-5 text-blue-500" />
            Sprint Progress
          </CardTitle>
          <Badge 
            variant="outline" 
            className={cn(
              'text-xs font-medium',
              overall_risk_level === 'HIGH' && 'bg-red-500/20 text-red-400 border-red-500/30',
              overall_risk_level === 'MEDIUM' && 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
              overall_risk_level === 'LOW' && 'bg-green-500/20 text-green-400 border-green-500/30'
            )}
          >
            {overall_risk_level} Risk
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-zinc-400">Completion</span>
            <span className="text-white font-medium">{completion_percentage}%</span>
          </div>
          <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div 
              className={cn('h-full transition-all duration-500', getProgressColor(completion_percentage))}
              style={{ width: `${completion_percentage}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <span>{completed_points} / {total_points} story points</span>
            <span>{remaining_points} remaining</span>
          </div>
        </div>

        {/* Metrics grid */}
        <div className="grid grid-cols-2 gap-2">
          <MetricCard 
            icon={CheckCircle2} 
            label="Completed" 
            value={completed_tasks}
            subValue={`of ${total_tasks} tasks`}
            color="green"
          />
          <MetricCard 
            icon={Clock} 
            label="In Progress" 
            value={in_progress_tasks}
            color="blue"
          />
          <MetricCard 
            icon={TrendingUp} 
            label="Story Points" 
            value={total_points}
            subValue={`${completed_points} done`}
            color="purple"
          />
          <MetricCard 
            icon={Users} 
            label="Tasks" 
            value={total_tasks}
            color="blue"
          />
        </div>

        {/* Warning badges */}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-white/5">
          <WarningBadge count={overdue_tasks} label="Overdue" color="red" />
          <WarningBadge count={blocked_tasks} label="Blocked" color="purple" />
          <WarningBadge count={unassigned_tasks} label="Unassigned" color="orange" />
        </div>
      </CardContent>
    </Card>
  );
}
