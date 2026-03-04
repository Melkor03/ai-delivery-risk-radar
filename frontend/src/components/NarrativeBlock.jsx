import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { Brain, Lightbulb, TrendingUp } from 'lucide-react';

export const NarrativeBlock = ({ title, content, recommendations, impact, riskLevel }) => {
  const getBorderColor = () => {
    switch (riskLevel?.toUpperCase()) {
      case 'HIGH': return 'border-l-red-500';
      case 'MEDIUM': return 'border-l-amber-500';
      case 'LOW': return 'border-l-emerald-500';
      default: return 'border-l-zinc-500';
    }
  };

  return (
    <div className="space-y-6">
      {/* AI Narrative */}
      <Card className={cn("bg-zinc-900/50 border-white/10 border-l-4", getBorderColor())} data-testid="narrative-block">
        <CardHeader className="border-b border-white/10">
          <CardTitle className="text-white flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-500" />
            {title || 'AI Analysis'}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <p className="text-zinc-300 leading-relaxed">{content}</p>
        </CardContent>
      </Card>

      {/* Impact Prediction */}
      {impact && (
        <Card className="bg-zinc-900/50 border-white/10">
          <CardHeader className="border-b border-white/10">
            <CardTitle className="text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-500" />
              Impact Prediction
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-zinc-800/50 border border-white/5">
                <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Timeline Impact</p>
                <p className="text-white">{impact.timeline_impact || 'Unknown'}</p>
              </div>
              <div className="p-4 rounded-lg bg-zinc-800/50 border border-white/5">
                <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Cost Impact</p>
                <p className="text-white">{impact.cost_impact || 'Unknown'}</p>
              </div>
              <div className="p-4 rounded-lg bg-zinc-800/50 border border-white/5">
                <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Quality Impact</p>
                <p className="text-white">{impact.quality_impact || 'Unknown'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <Card className="bg-zinc-900/50 border-white/10">
          <CardHeader className="border-b border-white/10">
            <CardTitle className="text-white flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-amber-500" />
              Recommended Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <ul className="space-y-3">
              {recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="w-6 h-6 rounded-full bg-amber-500/10 text-amber-500 flex items-center justify-center shrink-0 text-sm font-mono">
                    {i + 1}
                  </span>
                  <span className="text-zinc-300">{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
