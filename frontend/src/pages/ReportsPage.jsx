import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { getProjects } from '@/lib/api';
import api from '@/lib/api';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { 
  FileText, 
  Download, 
  Clock,
  Building,
  FolderKanban,
  FileCheck,
  Loader2
} from 'lucide-react';

export default function ReportsPage() {
  const [projects, setProjects] = useState([]);
  const [selectedProjects, setSelectedProjects] = useState([]);
  const [organizationName, setOrganizationName] = useState('');
  const [generating, setGenerating] = useState(false);
  const [reportHistory, setReportHistory] = useState([]);
  const [selectAll, setSelectAll] = useState(true);

  useEffect(() => {
    fetchProjects();
    fetchReportHistory();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await getProjects();
      setProjects(response.data);
      setSelectedProjects(response.data.map(p => p.id));
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    }
  };

  const fetchReportHistory = async () => {
    try {
      const response = await api.get('/reports/history');
      setReportHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch report history:', error);
    }
  };

  const handleSelectAll = (checked) => {
    setSelectAll(checked);
    if (checked) {
      setSelectedProjects(projects.map(p => p.id));
    } else {
      setSelectedProjects([]);
    }
  };

  const handleProjectToggle = (projectId) => {
    setSelectedProjects(prev => {
      if (prev.includes(projectId)) {
        return prev.filter(id => id !== projectId);
      } else {
        return [...prev, projectId];
      }
    });
  };

  const handleGenerateExecutiveReport = async () => {
    if (selectedProjects.length === 0) {
      toast.error('Please select at least one project');
      return;
    }

    setGenerating(true);
    try {
      const response = await api.post('/reports/executive', {
        organization_name: organizationName || 'Organization',
        include_projects: selectAll ? null : selectedProjects
      }, {
        responseType: 'blob'
      });

      // Create download link
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Risk_Radar_Executive_Report_${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success('Executive report downloaded');
      fetchReportHistory();
    } catch (error) {
      console.error('Failed to generate report:', error);
      toast.error('Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateProjectReport = async (projectId, projectName) => {
    setGenerating(true);
    try {
      const response = await api.post(`/reports/project/${projectId}`, {}, {
        responseType: 'blob'
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Risk_Report_${projectName.replace(/\s+/g, '_')}_${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success(`Report for ${projectName} downloaded`);
    } catch (error) {
      console.error('Failed to generate report:', error);
      toast.error('Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const getRiskColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'HIGH': return 'text-red-500 border-red-500/50';
      case 'MEDIUM': return 'text-amber-500 border-amber-500/50';
      case 'LOW': return 'text-emerald-500 border-emerald-500/50';
      default: return 'text-zinc-500 border-zinc-500/50';
    }
  };

  return (
    <div className="space-y-6" data-testid="reports-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Executive Reports</h1>
        <p className="text-zinc-500 mt-1">Generate comprehensive PDF reports for leadership</p>
      </div>

      {/* Executive Report Generator */}
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader className="border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <CardTitle className="text-white">Executive Risk Report</CardTitle>
              <CardDescription className="text-zinc-500">
                Comprehensive portfolio risk assessment for leadership review
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6 space-y-6">
          {/* Organization Name */}
          <div className="space-y-2">
            <Label className="text-zinc-300">Organization Name</Label>
            <div className="flex items-center gap-3">
              <Building className="w-4 h-4 text-zinc-500" />
              <Input
                value={organizationName}
                onChange={(e) => setOrganizationName(e.target.value)}
                placeholder="Enter your organization name"
                className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500 max-w-md"
                data-testid="org-name-input"
              />
            </div>
          </div>

          {/* Project Selection */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-zinc-300">Include Projects</Label>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="select-all"
                  checked={selectAll}
                  onCheckedChange={handleSelectAll}
                  className="border-zinc-600"
                />
                <label htmlFor="select-all" className="text-sm text-zinc-400">
                  Select All ({projects.length})
                </label>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-64 overflow-y-auto p-2 rounded-lg bg-zinc-800/30 border border-white/5">
              {projects.map(project => (
                <div
                  key={project.id}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-lg border transition-colors cursor-pointer",
                    selectedProjects.includes(project.id)
                      ? "bg-blue-500/10 border-blue-500/30"
                      : "bg-zinc-800/50 border-white/5 hover:border-white/10"
                  )}
                  onClick={() => handleProjectToggle(project.id)}
                >
                  <Checkbox
                    checked={selectedProjects.includes(project.id)}
                    onCheckedChange={() => handleProjectToggle(project.id)}
                    className="border-zinc-600"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white truncate">{project.name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className={cn("text-xs", getRiskColor(project.risk_level))}>
                        {project.risk_level || 'N/A'}
                      </Badge>
                      <span className="text-xs text-zinc-500">{project.risk_score}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Report Contents Preview */}
          <div className="p-4 rounded-lg bg-zinc-800/50 border border-white/5">
            <h4 className="text-sm font-medium text-white mb-3">Report Contents</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div className="flex items-center gap-2 text-zinc-400">
                <FileCheck className="w-4 h-4 text-emerald-500" />
                Executive Summary
              </div>
              <div className="flex items-center gap-2 text-zinc-400">
                <FileCheck className="w-4 h-4 text-emerald-500" />
                Risk Distribution
              </div>
              <div className="flex items-center gap-2 text-zinc-400">
                <FileCheck className="w-4 h-4 text-emerald-500" />
                Critical Projects
              </div>
              <div className="flex items-center gap-2 text-zinc-400">
                <FileCheck className="w-4 h-4 text-emerald-500" />
                AI Analysis
              </div>
              <div className="flex items-center gap-2 text-zinc-400">
                <FileCheck className="w-4 h-4 text-emerald-500" />
                Risk Dimensions
              </div>
              <div className="flex items-center gap-2 text-zinc-400">
                <FileCheck className="w-4 h-4 text-emerald-500" />
                Impact Predictions
              </div>
              <div className="flex items-center gap-2 text-zinc-400">
                <FileCheck className="w-4 h-4 text-emerald-500" />
                Recommendations
              </div>
              <div className="flex items-center gap-2 text-zinc-400">
                <FileCheck className="w-4 h-4 text-emerald-500" />
                Methodology
              </div>
            </div>
          </div>

          {/* Generate Button */}
          <div className="flex justify-end">
            <Button
              onClick={handleGenerateExecutiveReport}
              disabled={generating || selectedProjects.length === 0}
              className="bg-white text-black hover:bg-zinc-200"
              data-testid="generate-report-btn"
            >
              {generating ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4 mr-2" />
                  Generate Executive Report
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Individual Project Reports */}
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader className="border-b border-white/10">
          <CardTitle className="text-white flex items-center gap-2">
            <FolderKanban className="w-5 h-5 text-purple-500" />
            Individual Project Reports
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          {projects.length > 0 ? (
            <div className="divide-y divide-white/5">
              {projects.map(project => (
                <div key={project.id} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className={cn("", getRiskColor(project.risk_level))}>
                      {project.risk_level || 'N/A'}
                    </Badge>
                    <div>
                      <p className="text-sm font-medium text-white">{project.name}</p>
                      <p className="text-xs text-zinc-500">
                        Risk Score: {project.risk_score}% • Last analyzed: {project.last_analyzed ? new Date(project.last_analyzed).toLocaleDateString() : 'Never'}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleGenerateProjectReport(project.id, project.name)}
                    disabled={generating}
                    className="border-white/10 hover:bg-white/5"
                    data-testid={`download-report-${project.id}`}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Download
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-8 text-zinc-500">No projects found</p>
          )}
        </CardContent>
      </Card>

      {/* Report History */}
      {reportHistory.length > 0 && (
        <Card className="bg-zinc-900/50 border-white/10">
          <CardHeader className="border-b border-white/10">
            <CardTitle className="text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-500" />
              Recent Reports
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="space-y-2">
              {reportHistory.slice(0, 5).map((report, i) => (
                <div key={report.id || i} className="flex items-center justify-between p-3 rounded-lg bg-zinc-800/30">
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-zinc-500" />
                    <div>
                      <p className="text-sm text-white capitalize">{report.report_type} Report</p>
                      <p className="text-xs text-zinc-500">
                        {report.projects_included?.length || 0} projects included
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-zinc-500 font-mono">
                    {new Date(report.created_at).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
