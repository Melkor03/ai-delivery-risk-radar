// AtRiskTasksPanel.jsx - Shows tasks requiring immediate attention
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  AlertTriangle, 
  Clock, 
  Ban, 
  User, 
  Calendar,
  ExternalLink,
  ChevronRight,
  AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';

const riskFlagIcons = {
  overdue: { icon: Clock, color: 'text-red-500', bg: 'bg-red-500/10' },
  blocked: { icon: Ban, color: 'text-purple-500', bg: 'bg-purple-500/10' },
  unassigned: { icon: User, color: 'text-orange-500', bg: 'bg-orange-500/10' },
  no_due_date: { icon: Calendar, color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
  stale: { icon: AlertCircle, color: 'text-gray-500', bg: 'bg-gray-500/10' },
  high_complexity: { icon: AlertTriangle, color: 'text-blue-500', bg: 'bg-blue-500/10' },
  due_soon: { icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
};

const RiskBadge = ({ level }) => {
  const colors = {
    HIGH: 'bg-red-500/20 text-red-400 border-red-500/30',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    LOW: 'bg-green-500/20 text-green-400 border-green-500/30',
  };
  
  return (
    <Badge variant="outline" className={cn('text-xs font-medium', colors[level] || colors.LOW)}>
      {level}
    </Badge>
  );
};

const TaskRiskFlag = ({ flag }) => {
  const config = riskFlagIcons[flag.type] || riskFlagIcons.stale;
  const Icon = config.icon;
  
  return (
    <div className={cn('flex items-center gap-1.5 px-2 py-1 rounded-md text-xs', config.bg, config.color)}>
      <Icon className="w-3 h-3" />
      <span>{flag.message}</span>
    </div>
  );
};

export default function AtRiskTasksPanel({ tasks = [], onViewAll, loading = false }) {
  // Filter to high and medium risk tasks
  const atRiskTasks = tasks
    .filter(t => t.risk_level === 'HIGH' || t.risk_level === 'MEDIUM')
    .sort((a, b) => b.risk_score - a.risk_score)
    .slice(0, 5);
  
  const highRiskCount = tasks.filter(t => t.risk_level === 'HIGH').length;
  const mediumRiskCount = tasks.filter(t => t.risk_level === 'MEDIUM').length;

  if (loading) {
    return (
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            At-Risk Tasks
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-zinc-800/50 rounded-lg animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-zinc-900/50 border-white/10">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-white">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            At-Risk Tasks
          </CardTitle>
          <div className="flex items-center gap-2">
            {highRiskCount > 0 && (
              <Badge variant="outline" className="bg-red-500/20 text-red-400 border-red-500/30">
                {highRiskCount} High
              </Badge>
            )}
            {mediumRiskCount > 0 && (
              <Badge variant="outline" className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
                {mediumRiskCount} Medium
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {atRiskTasks.length === 0 ? (
          <div className="text-center py-8 text-zinc-400">
            <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center mx-auto mb-3">
              <AlertTriangle className="w-6 h-6 text-green-500" />
            </div>
            <p className="font-medium text-green-400">All Clear!</p>
            <p className="text-sm text-zinc-500 mt-1">No high-risk tasks identified</p>
          </div>
        ) : (
          <div className="space-y-3">
            {atRiskTasks.map((task, index) => (
              <div 
                key={task.task_id || index}
                className={cn(
                  "p-3 rounded-lg border transition-colors",
                  task.risk_level === 'HIGH' 
                    ? "bg-red-500/5 border-red-500/20 hover:border-red-500/40" 
                    : "bg-yellow-500/5 border-yellow-500/20 hover:border-yellow-500/40"
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <RiskBadge level={task.risk_level} />
                      <span className="text-xs text-zinc-500">
                        Score: {task.risk_score}
                      </span>
                    </div>
                    <h4 className="text-sm font-medium text-white truncate">
                      {task.name}
                    </h4>
                    <div className="flex items-center gap-2 mt-1 text-xs text-zinc-400">
                      <span>{task.assignees?.length > 0 ? task.assignees[0] : 'Unassigned'}</span>
                      {task.story_points && (
                        <>
                          <span>•</span>
                          <span>{task.story_points} pts</span>
                        </>
                      )}
                      {task.list_name && (
                        <>
                          <span>•</span>
                          <span className="truncate">{task.list_name}</span>
                        </>
                      )}
                    </div>
                  </div>
                  {task.url && (
                    <a 
                      href={task.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-zinc-500 hover:text-white transition-colors"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
                
                {/* Risk Flags */}
                {task.flags && task.flags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {task.flags.slice(0, 3).map((flag, i) => (
                      <TaskRiskFlag key={i} flag={flag} />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        
        {tasks.length > 5 && onViewAll && (
          <Button 
            variant="ghost" 
            className="w-full mt-3 text-zinc-400 hover:text-white"
            onClick={onViewAll}
          >
            View All Tasks
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
