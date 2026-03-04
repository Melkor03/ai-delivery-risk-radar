// ProjectDetailPage.jsx - Complete project analytics with all features
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  ArrowLeft,
  RefreshCw,
  Download,
  Play,
  Settings,
  BarChart3,
  ListTodo,
  GitBranch,
  TrendingUp,
  MessageSquare,
  Bell,
  Calendar,
  Target,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  Camera
} from 'lucide-react';
import { toast } from 'sonner';
import api from '@/lib/api';
import { cn } from '@/lib/utils';

// Import all component modules
import { RiskRadarChart } from '@/components/RiskRadarChart';
import AtRiskTasksPanel from '@/components/AtRiskTasksPanel';
import SprintProgressCard from '@/components/SprintProgressCard';
import BurndownChart from '@/components/BurndownChart';
import StandupSummaryCard from '@/components/StandupSummaryCard';
import RiskTrendsChart from '@/components/RiskTrendsChart';
import DependencyGraph from '@/components/DependencyGraph';
import NotificationSettings from '@/components/NotificationSettings';

// Task Risk Table Component
const TaskRiskTable = ({ tasks, loading }) => {
  const [sortBy, setSortBy] = useState('risk_score');
  const [sortDir, setSortDir] = useState('desc');
  const [filter, setFilter] = useState('all');

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="h-16 bg-zinc-800/50 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  const filteredTasks = tasks.filter(t => {
    if (filter === 'all') return true;
    if (filter === 'high') return t.risk_level === 'HIGH';
    if (filter === 'medium') return t.risk_level === 'MEDIUM';
    if (filter === 'overdue') return t.flags?.some(f => f.type === 'overdue');
    if (filter === 'blocked') return t.flags?.some(f => f.type === 'blocked');
    return true;
  });

  const sortedTasks = [...filteredTasks].sort((a, b) => {
    const aVal = a[sortBy] || 0;
    const bVal = b[sortBy] || 0;
    return sortDir === 'desc' ? bVal - aVal : aVal - bVal;
  });

  const getRiskBadgeClass = (level) => {
    switch (level) {
      case 'HIGH': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'MEDIUM': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      default: return 'bg-green-500/20 text-green-400 border-green-500/30';
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        {['all', 'high', 'medium', 'overdue', 'blocked'].map(f => (
          <Button
            key={f}
            variant="ghost"
            size="sm"
            className={cn(
              'h-8 text-xs',
              filter === f ? 'bg-zinc-700 text-white' : 'text-zinc-400'
            )}
            onClick={() => setFilter(f)}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f !== 'all' && (
              <Badge variant="outline" className="ml-1.5 h-4 text-[10px] px-1">
                {tasks.filter(t => {
                  if (f === 'high') return t.risk_level === 'HIGH';
                  if (f === 'medium') return t.risk_level === 'MEDIUM';
                  if (f === 'overdue') return t.flags?.some(fl => fl.type === 'overdue');
                  if (f === 'blocked') return t.flags?.some(fl => fl.type === 'blocked');
                  return false;
                }).length}
              </Badge>
            )}
          </Button>
        ))}
      </div>

      {/* Table */}
      <div className="border border-white/10 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-zinc-800/50 text-left text-xs text-zinc-400">
              <th className="px-4 py-3 font-medium">Task</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Assignee</th>
              <th className="px-4 py-3 font-medium cursor-pointer hover:text-white" onClick={() => {
                setSortBy('risk_score');
                setSortDir(d => d === 'desc' ? 'asc' : 'desc');
              }}>
                Risk {sortBy === 'risk_score' && (sortDir === 'desc' ? '↓' : '↑')}
              </th>
              <th className="px-4 py-3 font-medium">Flags</th>
              <th className="px-4 py-3 font-medium">Points</th>
              <th className="px-4 py-3 font-medium w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {sortedTasks.slice(0, 50).map((task, i) => (
              <tr 
                key={task.task_id || i} 
                className={cn(
                  "hover:bg-zinc-800/30 transition-colors",
                  task.risk_level === 'HIGH' && 'bg-red-500/5'
                )}
              >
                <td className="px-4 py-3">
                  <div className="max-w-xs">
                    <p className="text-sm text-white truncate">{task.name}</p>
                    {task.list_name && (
                      <p className="text-xs text-zinc-500 truncate">{task.list_name}</p>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs text-zinc-300">{task.status}</span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs text-zinc-400">
                    {task.assignees?.length > 0 ? task.assignees[0] : 'Unassigned'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <Badge variant="outline" className={cn('text-xs', getRiskBadgeClass(task.risk_level))}>
                    {task.risk_level} ({task.risk_score})
                  </Badge>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {task.flags?.slice(0, 2).map((flag, j) => (
                      <span 
                        key={j} 
                        className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-700 text-zinc-300"
                        title={flag.message}
                      >
                        {flag.type.slice(0, 3).toUpperCase()}
                      </span>
                    ))}
                    {task.flags?.length > 2 && (
                      <span className="text-[10px] text-zinc-500">+{task.flags.length - 2}</span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs text-zinc-400">
                    {task.story_points || '-'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {task.url && (
                    <a 
                      href={task.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-zinc-500 hover:text-white"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sortedTasks.length === 0 && (
          <div className="py-8 text-center text-zinc-500">
            No tasks match the current filter
          </div>
        )}
      </div>
    </div>
  );
};

// Sprint Config Modal
const SprintConfigForm = ({ projectId, onSave }) => {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [sprintName, setSprintName] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!startDate || !endDate) {
      toast.error('Please set both start and end dates');
      return;
    }

    try {
      setSaving(true);
      await api.post(`/projects/${projectId}/sprint-config`, {
        project_id: projectId,
        sprint_name: sprintName,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString()
      });
      toast.success('Sprint configuration saved!');
      if (onSave) onSave();
    } catch (error) {
      toast.error('Failed to save sprint config');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="bg-zinc-800/50 border-white/10">
      <CardHeader className="pb-3">
        <CardTitle className="text-base text-white flex items-center gap-2">
          <Calendar className="w-4 h-4" />
          Sprint Configuration
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label className="text-zinc-400 text-xs">Sprint Name (optional)</Label>
            <Input
              value={sprintName}
              onChange={e => setSprintName(e.target.value)}
              placeholder="Sprint 1"
              className="bg-zinc-900 border-zinc-700 text-white mt-1"
            />
          </div>
          <div>
            <Label className="text-zinc-400 text-xs">Start Date</Label>
            <Input
              type="date"
              value={startDate}
              onChange={e => setStartDate(e.target.value)}
              className="bg-zinc-900 border-zinc-700 text-white mt-1"
            />
          </div>
          <div>
            <Label className="text-zinc-400 text-xs">End Date</Label>
            <Input
              type="date"
              value={endDate}
              onChange={e => setEndDate(e.target.value)}
              className="bg-zinc-900 border-zinc-700 text-white mt-1"
            />
          </div>
        </div>
        <Button onClick={handleSave} disabled={saving} size="sm">
          {saving ? 'Saving...' : 'Save Sprint Config'}
        </Button>
      </CardContent>
    </Card>
  );
};

// Main Component
export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  
  const [project, setProject] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [taskAnalysis, setTaskAnalysis] = useState(null);
  const [burndownData, setBurndownData] = useState(null);
  const [standupData, setStandupData] = useState(null);
  const [trendsData, setTrendsData] = useState([]);
  const [dependencyData, setDependencyData] = useState(null);

  useEffect(() => {
    fetchAllData();
  }, [projectId]);

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchProject(),
      fetchTaskAnalysis(),
      fetchBurndown(),
      fetchStandup(),
      fetchTrends(),
      fetchDependencies()
    ]);
    setLoading(false);
  };

  const fetchProject = async () => {
    try {
      const response = await api.get(`/projects/${projectId}`);
      setProject(response.data);
      
      // Get latest assessment
      const assessments = await api.get(`/projects/${projectId}/assessments`);
      if (assessments.data?.length > 0) {
        setAssessment(assessments.data[0]);
      }
    } catch (error) {
      console.error('Failed to fetch project:', error);
    }
  };

  const fetchTaskAnalysis = async () => {
    try {
      const response = await api.get(`/projects/${projectId}/task-analysis`);
      setTaskAnalysis(response.data);
    } catch (error) {
      console.log('Task analysis not available');
    }
  };

  const fetchBurndown = async () => {
    try {
      const response = await api.get(`/projects/${projectId}/burndown`);
      setBurndownData(response.data);
    } catch (error) {
      console.log('Burndown not available');
    }
  };

  const fetchStandup = async () => {
    try {
      const response = await api.get(`/projects/${projectId}/standup`);
      setStandupData(response.data);
    } catch (error) {
      console.log('Standup not available');
    }
  };

  const fetchTrends = async (days = 14) => {
    try {
      const response = await api.get(`/projects/${projectId}/trends?days=${days}`);
      setTrendsData(response.data.trends || []);
    } catch (error) {
      console.log('Trends not available');
    }
  };

  const fetchDependencies = async () => {
    try {
      const response = await api.get(`/projects/${projectId}/dependencies`);
      setDependencyData(response.data);
    } catch (error) {
      console.log('Dependencies not available');
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchAllData();
    setRefreshing(false);
    toast.success('Data refreshed');
  };

  const handleRunAnalysis = async () => {
    try {
      setAnalyzing(true);
      await api.post(`/projects/${projectId}/analyze`);
      
      // Create snapshot for trends
      await api.post(`/projects/${projectId}/snapshot`);
      
      await fetchAllData();
      toast.success('Analysis complete!');
    } catch (error) {
      toast.error('Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleDownloadReport = async () => {
    try {
      toast.loading('Generating report...');
      const response = await api.post(`/reports/project/${projectId}`, {}, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${project?.name || 'Project'}_Risk_Report_${new Date().toISOString().split('T')[0]}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      
      toast.dismiss();
      toast.success('Report downloaded!');
    } catch (error) {
      toast.dismiss();
      toast.error('Failed to generate report');
    }
  };

  if (loading && !project) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  const summary = taskAnalysis?.summary || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/projects')}
            className="text-zinc-400 hover:text-white"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-white">{project?.name}</h1>
            <p className="text-zinc-400 mt-1">{project?.description || 'No description'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
            className="border-zinc-700"
          >
            <RefreshCw className={cn("w-4 h-4 mr-2", refreshing && "animate-spin")} />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={handleRunAnalysis}
            disabled={analyzing}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Play className={cn("w-4 h-4 mr-2", analyzing && "animate-pulse")} />
            {analyzing ? 'Analyzing...' : 'Run Analysis'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadReport}
            className="border-zinc-700"
          >
            <Download className="w-4 h-4 mr-2" />
            Export PDF
          </Button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <Card className="bg-zinc-900/50 border-white/10">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className={cn(
                "p-2 rounded-lg",
                summary.overall_risk_level === 'HIGH' && 'bg-red-500/20',
                summary.overall_risk_level === 'MEDIUM' && 'bg-yellow-500/20',
                summary.overall_risk_level === 'LOW' && 'bg-green-500/20',
                !summary.overall_risk_level && 'bg-zinc-500/20'
              )}>
                <Target className={cn(
                  "w-5 h-5",
                  summary.overall_risk_level === 'HIGH' && 'text-red-400',
                  summary.overall_risk_level === 'MEDIUM' && 'text-yellow-400',
                  summary.overall_risk_level === 'LOW' && 'text-green-400',
                  !summary.overall_risk_level && 'text-zinc-400'
                )} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{summary.average_risk_score || 0}%</p>
                <p className="text-xs text-zinc-500">Risk Score</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-zinc-900/50 border-white/10">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/20">
                <ListTodo className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{summary.total_tasks || 0}</p>
                <p className="text-xs text-zinc-500">Total Tasks</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900/50 border-white/10">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/20">
                <CheckCircle2 className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{summary.completion_percentage || 0}%</p>
                <p className="text-xs text-zinc-500">Complete</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900/50 border-white/10">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/20">
                <AlertTriangle className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{summary.high_risk_tasks || 0}</p>
                <p className="text-xs text-zinc-500">High Risk</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900/50 border-white/10">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-yellow-500/20">
                <Clock className="w-5 h-5 text-yellow-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{summary.overdue_tasks || 0}</p>
                <p className="text-xs text-zinc-500">Overdue</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900/50 border-white/10">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/20">
                <GitBranch className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{summary.blocked_tasks || 0}</p>
                <p className="text-xs text-zinc-500">Blocked</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="bg-zinc-800/50 border border-white/10">
          <TabsTrigger value="overview" className="data-[state=active]:bg-zinc-700">
            <BarChart3 className="w-4 h-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="tasks" className="data-[state=active]:bg-zinc-700">
            <ListTodo className="w-4 h-4 mr-2" />
            Tasks
          </TabsTrigger>
          <TabsTrigger value="dependencies" className="data-[state=active]:bg-zinc-700">
            <GitBranch className="w-4 h-4 mr-2" />
            Dependencies
          </TabsTrigger>
          <TabsTrigger value="trends" className="data-[state=active]:bg-zinc-700">
            <TrendingUp className="w-4 h-4 mr-2" />
            Trends
          </TabsTrigger>
          <TabsTrigger value="standup" className="data-[state=active]:bg-zinc-700">
            <MessageSquare className="w-4 h-4 mr-2" />
            Standup
          </TabsTrigger>
          <TabsTrigger value="settings" className="data-[state=active]:bg-zinc-700">
            <Settings className="w-4 h-4 mr-2" />
            Settings
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <SprintProgressCard data={summary} loading={loading} />
              <BurndownChart data={burndownData} loading={loading} />
              {assessment?.risk_dimensions && (
                <Card className="bg-zinc-900/50 border-white/10">
                  <CardHeader>
                    <CardTitle className="text-white">Risk Radar</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <RiskRadarChart dimensions={assessment.risk_dimensions} />
                  </CardContent>
                </Card>
              )}
            </div>
            <div className="space-y-6">
              <AtRiskTasksPanel 
                tasks={taskAnalysis?.tasks || []} 
                loading={loading}
              />
              <StandupSummaryCard 
                data={standupData} 
                loading={loading}
                onRefresh={fetchStandup}
              />
            </div>
          </div>
        </TabsContent>

        {/* Tasks Tab */}
        <TabsContent value="tasks">
          <Card className="bg-zinc-900/50 border-white/10">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <ListTodo className="w-5 h-5" />
                Task Risk Analysis
              </CardTitle>
              <CardDescription className="text-zinc-400">
                All tasks sorted by risk score with individual risk flags
              </CardDescription>
            </CardHeader>
            <CardContent>
              <TaskRiskTable tasks={taskAnalysis?.tasks || []} loading={loading} />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Dependencies Tab */}
        <TabsContent value="dependencies">
          <DependencyGraph data={dependencyData} loading={loading} />
        </TabsContent>

        {/* Trends Tab */}
        <TabsContent value="trends">
          <RiskTrendsChart 
            trends={trendsData} 
            loading={loading}
            onPeriodChange={fetchTrends}
          />
        </TabsContent>

        {/* Standup Tab */}
        <TabsContent value="standup" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <StandupSummaryCard 
              data={standupData} 
              loading={loading}
              onRefresh={fetchStandup}
            />
            <Card className="bg-zinc-900/50 border-white/10">
              <CardHeader>
                <CardTitle className="text-white text-base">Team Workload</CardTitle>
              </CardHeader>
              <CardContent>
                {summary.assignee_workload && Object.entries(summary.assignee_workload).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(summary.assignee_workload).map(([name, data]) => (
                      <div key={name} className="flex items-center justify-between p-2 rounded bg-zinc-800/50">
                        <span className="text-sm text-white">{name}</span>
                        <div className="flex items-center gap-4 text-xs text-zinc-400">
                          <span>{data.total} tasks</span>
                          <span>{data.in_progress} active</span>
                          <span>{data.points} pts</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-zinc-500 text-center py-4">No workload data available</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings" className="space-y-6">
          <SprintConfigForm projectId={projectId} onSave={handleRefresh} />
          <NotificationSettings />
        </TabsContent>
      </Tabs>
    </div>
  );
}
