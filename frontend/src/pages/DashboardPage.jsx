// DashboardPage.jsx - Enhanced Dashboard with Task-Level Intelligence
import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Radar, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle2,
  Clock,
  FolderKanban,
  RefreshCw,
  Download,
  ChevronRight,
  BarChart3,
  Zap,
  Calendar
} from 'lucide-react';
import { toast } from 'sonner';
import api from '@/lib/api';
import { RiskRadarChart } from '@/components/RiskRadarChart';
import AtRiskTasksPanel from '@/components/AtRiskTasksPanel';
import SprintProgressCard from '@/components/SprintProgressCard';
import BurndownChart from '@/components/BurndownChart';
import StandupSummaryCard from '@/components/StandupSummaryCard';
import { cn } from '@/lib/utils';

const MetricCard = ({ icon: Icon, label, value, trend, color = 'blue', onClick }) => {
  const colors = {
    blue: 'from-blue-500/20 to-blue-600/10 border-blue-500/20',
    green: 'from-green-500/20 to-green-600/10 border-green-500/20',
    red: 'from-red-500/20 to-red-600/10 border-red-500/20',
    yellow: 'from-yellow-500/20 to-yellow-600/10 border-yellow-500/20',
    purple: 'from-purple-500/20 to-purple-600/10 border-purple-500/20',
  };

  const iconColors = {
    blue: 'text-blue-400',
    green: 'text-green-400',
    red: 'text-red-400',
    yellow: 'text-yellow-400',
    purple: 'text-purple-400',
  };

  return (
    <Card 
      className={cn(
        "bg-gradient-to-br border cursor-pointer hover:border-opacity-50 transition-all",
        colors[color]
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-2xl font-bold text-white">{value}</p>
            <p className="text-sm text-zinc-400">{label}</p>
          </div>
          <div className={cn("p-3 rounded-xl bg-white/5", iconColors[color])}>
            <Icon className="w-5 h-5" />
          </div>
        </div>
        {trend && (
          <div className="mt-2 flex items-center gap-1 text-xs">
            <TrendingUp className={cn("w-3 h-3", trend > 0 ? 'text-green-400' : 'text-red-400')} />
            <span className={trend > 0 ? 'text-green-400' : 'text-red-400'}>
              {trend > 0 ? '+' : ''}{trend}% from last week
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [taskAnalysis, setTaskAnalysis] = useState(null);
  const [burndownData, setBurndownData] = useState(null);
  const [standupData, setStandupData] = useState(null);
  const [summary, setSummary] = useState({
    total: 0,
    highRisk: 0,
    mediumRisk: 0,
    lowRisk: 0
  });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      fetchProjectDetails(selectedProject);
    }
  }, [selectedProject]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/projects');
      const projectList = response.data || [];
      setProjects(projectList);

      // Calculate summary
      const high = projectList.filter(p => (p.risk_level || '').toUpperCase() === 'HIGH').length;
      const medium = projectList.filter(p => (p.risk_level || '').toUpperCase() === 'MEDIUM').length;
      const low = projectList.filter(p => (p.risk_level || '').toUpperCase() === 'LOW').length;
      
      setSummary({
        total: projectList.length,
        highRisk: high,
        mediumRisk: medium,
        lowRisk: low
      });

      // Auto-select first project if available
      if (projectList.length > 0 && !selectedProject) {
        setSelectedProject(projectList[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch projects:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const fetchProjectDetails = async (projectId) => {
    try {
      setRefreshing(true);
      
      // Fetch task analysis
      try {
        const analysisRes = await api.get(`/projects/${projectId}/task-analysis`);
        setTaskAnalysis(analysisRes.data);
      } catch (e) {
        console.log('Task analysis not available yet');
        setTaskAnalysis(null);
      }

      // Fetch burndown data
      try {
        const burndownRes = await api.get(`/projects/${projectId}/burndown`);
        setBurndownData(burndownRes.data);
      } catch (e) {
        console.log('Burndown data not available yet');
        setBurndownData(null);
      }

      // Fetch standup summary
      try {
        const standupRes = await api.get(`/projects/${projectId}/standup`);
        setStandupData(standupRes.data);
      } catch (e) {
        console.log('Standup data not available yet');
        setStandupData(null);
      }
    } catch (error) {
      console.error('Failed to fetch project details:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    if (selectedProject) {
      fetchProjectDetails(selectedProject);
    }
    fetchData();
  };

  const handleGenerateReport = async () => {
    try {
      toast.loading('Generating report...');
      const response = await api.post('/reports/executive', {}, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Risk_Radar_Report_${new Date().toISOString().split('T')[0]}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      
      toast.dismiss();
      toast.success('Report downloaded!');
    } catch (error) {
      toast.dismiss();
      toast.error('Failed to generate report');
    }
  };

  const currentProject = projects.find(p => p.id === selectedProject);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-zinc-400 mt-1">Monitor delivery risks across your projects</p>
        </div>
        <div className="flex items-center gap-3">
          {projects.length > 0 && (
            <Select value={selectedProject || ''} onValueChange={setSelectedProject}>
              <SelectTrigger className="w-[200px] bg-zinc-800 border-zinc-700 text-white">
                <SelectValue placeholder="Select project" />
              </SelectTrigger>
              <SelectContent className="bg-zinc-800 border-zinc-700">
                {projects.map(project => (
                  <SelectItem key={project.id} value={project.id} className="text-white hover:bg-zinc-700">
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
            className="border-zinc-700 text-zinc-300 hover:text-white"
          >
            <RefreshCw className={cn("w-4 h-4 mr-2", refreshing && "animate-spin")} />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={handleGenerateReport}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Download className="w-4 h-4 mr-2" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Overview Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={FolderKanban}
          label="Total Projects"
          value={summary.total}
          color="blue"
          onClick={() => navigate('/projects')}
        />
        <MetricCard
          icon={AlertTriangle}
          label="High Risk"
          value={summary.highRisk}
          color="red"
          onClick={() => navigate('/projects?filter=high')}
        />
        <MetricCard
          icon={Clock}
          label="Medium Risk"
          value={summary.mediumRisk}
          color="yellow"
          onClick={() => navigate('/projects?filter=medium')}
        />
        <MetricCard
          icon={CheckCircle2}
          label="Low Risk"
          value={summary.lowRisk}
          color="green"
          onClick={() => navigate('/projects?filter=low')}
        />
      </div>

      {/* Main Content Grid */}
      {selectedProject && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Sprint Progress & Burndown */}
          <div className="lg:col-span-2 space-y-6">
            {/* Sprint Progress */}
            <SprintProgressCard 
              data={taskAnalysis?.summary} 
              loading={refreshing && !taskAnalysis}
            />

            {/* Burndown Chart */}
            <BurndownChart 
              data={burndownData} 
              loading={refreshing && !burndownData}
            />

            {/* Risk Radar */}
            {currentProject?.risk_dimensions && (
              <Card className="bg-zinc-900/50 border-white/10">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-white">
                    <Radar className="w-5 h-5 text-blue-500" />
                    Risk Radar
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <RiskRadarChart dimensions={currentProject.risk_dimensions} />
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - At Risk Tasks & Standup */}
          <div className="space-y-6">
            {/* At-Risk Tasks */}
            <AtRiskTasksPanel
              tasks={taskAnalysis?.tasks || []}
              loading={refreshing && !taskAnalysis}
              onViewAll={() => navigate(`/projects/${selectedProject}`)}
            />

            {/* Daily Standup */}
            <StandupSummaryCard
              data={standupData}
              loading={refreshing && !standupData}
              onRefresh={() => fetchProjectDetails(selectedProject)}
            />

            {/* Quick Actions */}
            <Card className="bg-zinc-900/50 border-white/10">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-white text-base">
                  <Zap className="w-4 h-4 text-yellow-500" />
                  Quick Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button
                  variant="ghost"
                  className="w-full justify-start text-zinc-300 hover:text-white hover:bg-zinc-800"
                  onClick={() => navigate('/data-upload')}
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Sync ClickUp Data
                  <ChevronRight className="w-4 h-4 ml-auto" />
                </Button>
                <Button
                  variant="ghost"
                  className="w-full justify-start text-zinc-300 hover:text-white hover:bg-zinc-800"
                  onClick={() => navigate(`/projects/${selectedProject}`)}
                >
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Run Risk Analysis
                  <ChevronRight className="w-4 h-4 ml-auto" />
                </Button>
                <Button
                  variant="ghost"
                  className="w-full justify-start text-zinc-300 hover:text-white hover:bg-zinc-800"
                  onClick={() => navigate('/reports')}
                >
                  <Calendar className="w-4 h-4 mr-2" />
                  View Reports
                  <ChevronRight className="w-4 h-4 ml-auto" />
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && projects.length === 0 && (
        <Card className="bg-zinc-900/50 border-white/10">
          <CardContent className="py-12 text-center">
            <FolderKanban className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No Projects Yet</h3>
            <p className="text-zinc-400 mb-4">Create your first project to start monitoring delivery risks.</p>
            <Button onClick={() => navigate('/projects')} className="bg-blue-600 hover:bg-blue-700">
              Create Project
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
