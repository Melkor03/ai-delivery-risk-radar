// StandupSummaryCard.jsx - Daily standup summary
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  MessageSquare, 
  CheckCircle2, 
  Clock, 
  AlertTriangle,
  Copy,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Send
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

export default function StandupSummaryCard({ data, onRefresh, loading = false }) {
  const [expanded, setExpanded] = useState(false);

  if (loading) {
    return (
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <MessageSquare className="w-5 h-5 text-green-500" />
            Daily Standup
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-zinc-800/50 rounded-lg animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <MessageSquare className="w-5 h-5 text-green-500" />
            Daily Standup
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-zinc-400">
            <p>No standup data available.</p>
            <p className="text-sm text-zinc-500 mt-1">Sync your tasks first to generate standup summary.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const {
    date,
    completed_yesterday = [],
    in_progress_today = [],
    blockers = [],
    at_risk_tasks = [],
    key_metrics = {},
    talking_points = []
  } = data;

  const copyToClipboard = () => {
    const text = generateStandupText();
    navigator.clipboard.writeText(text);
    toast.success('Standup copied to clipboard!');
  };

  const generateStandupText = () => {
    let text = `📊 Daily Standup - ${date}\n\n`;
    
    if (completed_yesterday.length > 0) {
      text += `✅ Completed:\n`;
      completed_yesterday.forEach(t => {
        text += `• ${t.name}${t.points ? ` (${t.points} pts)` : ''}\n`;
      });
      text += '\n';
    }
    
    if (in_progress_today.length > 0) {
      text += `🔄 In Progress:\n`;
      in_progress_today.forEach(t => {
        text += `• ${t.name}${t.assignee ? ` (@${t.assignee})` : ''}\n`;
      });
      text += '\n';
    }
    
    if (blockers.length > 0) {
      text += `🚫 Blockers:\n`;
      blockers.forEach(b => {
        text += `• ${b.name}: ${b.reason}\n`;
      });
      text += '\n';
    }
    
    if (talking_points.length > 0) {
      text += `💬 Key Points:\n`;
      talking_points.forEach(p => {
        text += `• ${p}\n`;
      });
    }
    
    return text;
  };

  return (
    <Card className="bg-zinc-900/50 border-white/10">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-white">
            <MessageSquare className="w-5 h-5 text-green-500" />
            Daily Standup
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs text-zinc-400 border-zinc-700">
              {date || 'Today'}
            </Badge>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-zinc-400 hover:text-white"
              onClick={onRefresh}
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Quick metrics */}
        <div className="grid grid-cols-4 gap-2 p-3 rounded-lg bg-zinc-800/50">
          <div className="text-center">
            <p className="text-lg font-bold text-white">{key_metrics.total_tasks || 0}</p>
            <p className="text-xs text-zinc-500">Total</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-green-400">{key_metrics.completed || 0}</p>
            <p className="text-xs text-zinc-500">Done</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-blue-400">{key_metrics.in_progress || 0}</p>
            <p className="text-xs text-zinc-500">Active</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-white">{key_metrics.completion_pct || 0}%</p>
            <p className="text-xs text-zinc-500">Progress</p>
          </div>
        </div>

        {/* Talking points */}
        {talking_points.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Key Points</h4>
            <div className="space-y-1.5">
              {talking_points.slice(0, expanded ? 10 : 3).map((point, i) => (
                <p key={i} className="text-sm text-zinc-300 flex items-start gap-2">
                  <span className="text-zinc-500">•</span>
                  {point}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Blockers warning */}
        {blockers.length > 0 && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <h4 className="text-sm font-medium text-red-400">
                {blockers.length} Blocker{blockers.length > 1 ? 's' : ''}
              </h4>
            </div>
            <div className="space-y-1">
              {blockers.slice(0, 2).map((b, i) => (
                <p key={i} className="text-xs text-zinc-300 truncate">
                  {b.name}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Expandable sections */}
        {expanded && (
          <div className="space-y-4 pt-2 border-t border-white/5">
            {/* Completed yesterday */}
            {completed_yesterday.length > 0 && (
              <div>
                <h4 className="flex items-center gap-1.5 text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                  Completed
                </h4>
                <div className="space-y-1">
                  {completed_yesterday.map((t, i) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <span className="text-zinc-300 truncate">{t.name}</span>
                      {t.points && (
                        <Badge variant="outline" className="text-xs text-zinc-500 border-zinc-700 ml-2">
                          {t.points} pts
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* In progress */}
            {in_progress_today.length > 0 && (
              <div>
                <h4 className="flex items-center gap-1.5 text-xs font-medium text-zinc-400 uppercase tracking-wider mb-2">
                  <Clock className="w-3.5 h-3.5 text-blue-500" />
                  In Progress
                </h4>
                <div className="space-y-1">
                  {in_progress_today.slice(0, 5).map((t, i) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <span className="text-zinc-300 truncate">{t.name}</span>
                      <span className="text-xs text-zinc-500 ml-2">@{t.assignee}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-2 pt-2">
          <Button
            variant="ghost"
            size="sm"
            className="flex-1 text-zinc-400 hover:text-white"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <>
                <ChevronUp className="w-4 h-4 mr-1" />
                Show Less
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4 mr-1" />
                Show Details
              </>
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-zinc-400 hover:text-white"
            onClick={copyToClipboard}
          >
            <Copy className="w-4 h-4 mr-1" />
            Copy
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
