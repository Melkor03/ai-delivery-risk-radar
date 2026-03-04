import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getProjects, createEntry, syncClickUp, getClickUpConfig } from '@/lib/api';
import api from '@/lib/api';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { 
  Upload, 
  FileText, 
  FileJson,
  File,
  CheckCircle,
  X,
  RefreshCw,
  FileSpreadsheet,
  Link as LinkIcon,
  ListChecks
} from 'lucide-react';

export default function DataUploadPage() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  
  const [entryType, setEntryType] = useState('status_report');
  const [entryTitle, setEntryTitle] = useState('');
  const [entryContent, setEntryContent] = useState('');
  const [entryDate, setEntryDate] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [jiraConfigured, setJiraConfigured] = useState(false);
  const [syncingJira, setSyncingJira] = useState(false);

  const [sheetsConnected, setSheetsConnected] = useState(false);
  const [sheetUrl, setSheetUrl] = useState('');
  const [sheetName, setSheetName] = useState('Sheet1');
  const [syncingSheet, setSyncingSheet] = useState(false);

  const [clickupConfigured, setClickupConfigured] = useState(false);
  const [syncingClickUp, setSyncingClickUp] = useState(false);

  useEffect(() => {
    fetchProjects();
    checkConfigs();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await getProjects();
      setProjects(response.data);
      if (response.data.length > 0) {
        setSelectedProject(response.data[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    }
  };

  const checkConfigs = async () => {
    try {
      const jiraRes = await api.get('/settings/jira');
      setJiraConfigured(!!jiraRes.data?.instance_url);
    } catch (e) {}
    try {
      const sheetsRes = await api.get('/oauth/sheets/status');
      setSheetsConnected(sheetsRes.data.connected);
    } catch (e) {}
    try {
      const clickupRes = await getClickUpConfig();
      setClickupConfigured(!!clickupRes.data?.team_id || !!clickupRes.data?.space_id);
    } catch (e) {}
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    await handleFiles(files);
  };

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files);
    await handleFiles(files);
  };

  const handleFiles = async (files) => {
    if (!selectedProject) {
      toast.error('Please select a project first');
      return;
    }
    setUploading(true);
    for (const file of files) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('project_id', selectedProject);
        formData.append('data_type', 'auto');
        const response = await api.post('/uploads/with-mapping', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        setUploadedFiles(prev => [...prev, { 
          name: file.name, 
          status: 'success', 
          type: response.data.data_type,
          records: response.data.records_count
        }]);
        toast.success(`Uploaded ${file.name}`);
      } catch (error) {
        setUploadedFiles(prev => [...prev, { name: file.name, status: 'error' }]);
        toast.error(`Failed to upload ${file.name}`);
      }
    }
    setUploading(false);
  };

  const handleManualEntry = async (e) => {
    e.preventDefault();
    if (!selectedProject) {
      toast.error('Please select a project first');
      return;
    }
    setSubmitting(true);
    try {
      await createEntry({
        project_id: selectedProject,
        entry_type: entryType,
        title: entryTitle,
        content: entryContent,
        date: entryDate
      });
      toast.success('Entry added successfully');
      setEntryTitle('');
      setEntryContent('');
      setEntryDate('');
    } catch (error) {
      toast.error('Failed to add entry');
    } finally {
      setSubmitting(false);
    }
  };

  const handleJiraSync = async () => {
    if (!selectedProject) {
      toast.error('Please select a project first');
      return;
    }
    setSyncingJira(true);
    try {
      const response = await api.post('/jira/sync', { project_id: selectedProject });
      if (response.data.success) {
        toast.success(`Synced ${response.data.summary?.total_issues || 0} issues from Jira`);
      } else {
        toast.error(response.data.error || 'Sync failed');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to sync from Jira');
    } finally {
      setSyncingJira(false);
    }
  };

  const handleSyncSheet = async () => {
    if (!selectedProject || !sheetUrl) {
      toast.error('Please select a project and enter a sheet URL');
      return;
    }
    setSyncingSheet(true);
    try {
      const response = await api.post('/sheets/sync', {
        project_id: selectedProject,
        spreadsheet_url: sheetUrl,
        sheet_name: sheetName
      });
      if (response.data.success) {
        toast.success(`Imported ${response.data.records_imported} records`);
        setSheetUrl('');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import');
    } finally {
      setSyncingSheet(false);
    }
  };

  const handleClickUpSync = async () => {
    if (!selectedProject) {
      toast.error('Please select a project first');
      return;
    }
    setSyncingClickUp(true);
    try {
      const response = await syncClickUp({ project_id: selectedProject });
      if (response.data.success) {
        toast.success(`Synced ${response.data.summary?.total_tasks || 0} tasks from ClickUp`);
      } else {
        toast.error(response.data.error || 'Sync failed');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to sync from ClickUp');
    } finally {
      setSyncingClickUp(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="data-upload-page">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Data Upload</h1>
        <p className="text-zinc-500 mt-1">Import data from multiple sources for risk analysis</p>
      </div>

      <Card className="bg-zinc-900/50 border-white/10">
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <Label className="text-zinc-300 whitespace-nowrap">Select Project:</Label>
            <Select value={selectedProject} onValueChange={setSelectedProject}>
              <SelectTrigger className="w-full max-w-md bg-zinc-800 border-zinc-700 text-white" data-testid="project-select">
                <SelectValue placeholder="Select a project" />
              </SelectTrigger>
              <SelectContent className="bg-zinc-800 border-zinc-700">
                {projects.map(project => (
                  <SelectItem key={project.id} value={project.id} className="text-white hover:bg-zinc-700">
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="jira" className="space-y-6">
        <TabsList className="bg-zinc-900 border border-white/10">
          <TabsTrigger value="jira" className="data-[state=active]:bg-white data-[state=active]:text-black" data-testid="tab-jira">
            Jira Sync
          </TabsTrigger>
          <TabsTrigger value="clickup" className="data-[state=active]:bg-white data-[state=active]:text-black" data-testid="tab-clickup">
            <ListChecks className="w-4 h-4 mr-2" />
            ClickUp
          </TabsTrigger>
          <TabsTrigger value="sheets" className="data-[state=active]:bg-white data-[state=active]:text-black" data-testid="tab-sheets">
            <FileSpreadsheet className="w-4 h-4 mr-2" />
            Google Sheets
          </TabsTrigger>
          <TabsTrigger value="upload" className="data-[state=active]:bg-white data-[state=active]:text-black" data-testid="tab-upload">
            <Upload className="w-4 h-4 mr-2" />
            File Upload
          </TabsTrigger>
          <TabsTrigger value="manual" className="data-[state=active]:bg-white data-[state=active]:text-black" data-testid="tab-manual">
            <FileText className="w-4 h-4 mr-2" />
            Manual Entry
          </TabsTrigger>
        </TabsList>

        <TabsContent value="jira" className="space-y-6">
          <Card className="bg-zinc-900/50 border-white/10">
            <CardHeader className="border-b border-white/10">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white">Jira Full Sync</CardTitle>
                  <CardDescription className="text-zinc-500">
                    Pull sprint data, issues, and velocity metrics from Jira
                  </CardDescription>
                </div>
                {jiraConfigured ? (
                  <Badge className="bg-emerald-500/20 text-emerald-400">Configured</Badge>
                ) : (
                  <Badge variant="outline" className="text-amber-500 border-amber-500/50">Not Configured</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {jiraConfigured ? (
                <div className="flex items-center justify-between p-4 rounded-lg bg-zinc-800/50 border border-white/5">
                  <div>
                    <p className="font-medium text-white">Sync All Data</p>
                    <p className="text-sm text-zinc-500">Pull sprints, issues, velocity, and blocked tickets</p>
                  </div>
                  <Button
                    onClick={handleJiraSync}
                    disabled={syncingJira || !selectedProject}
                    className="bg-blue-600 hover:bg-blue-700"
                    data-testid="jira-sync-btn"
                  >
                    <RefreshCw className={cn("w-4 h-4 mr-2", syncingJira && "animate-spin")} />
                    {syncingJira ? 'Syncing...' : 'Sync Now'}
                  </Button>
                </div>
              ) : (
                <div className="text-center py-8">
                  <LinkIcon className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
                  <p className="text-zinc-400">Jira not configured</p>
                  <Button variant="outline" className="mt-4 border-white/10" onClick={() => window.location.href = '/settings'}>
                    Configure Jira
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="clickup" className="space-y-6">
          <Card className="bg-zinc-900/50 border-white/10">
            <CardHeader className="border-b border-white/10">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white">ClickUp Full Sync</CardTitle>
                  <CardDescription className="text-zinc-500">
                    Pull tasks, lists, and custom fields from ClickUp
                  </CardDescription>
                </div>
                {clickupConfigured ? (
                  <Badge className="bg-emerald-500/20 text-emerald-400">Configured</Badge>
                ) : (
                  <Badge variant="outline" className="text-amber-500 border-amber-500/50">Not Configured</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {clickupConfigured ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-lg bg-zinc-800/50 border border-white/5">
                    <div>
                      <p className="font-medium text-white">Sync All Tasks</p>
                      <p className="text-sm text-zinc-500">Pull tasks, statuses, assignees, and custom fields from all lists</p>
                    </div>
                    <Button
                      onClick={handleClickUpSync}
                      disabled={syncingClickUp || !selectedProject}
                      className="bg-purple-600 hover:bg-purple-700"
                      data-testid="clickup-sync-btn"
                    >
                      <RefreshCw className={cn("w-4 h-4 mr-2", syncingClickUp && "animate-spin")} />
                      {syncingClickUp ? 'Syncing...' : 'Sync Now'}
                    </Button>
                  </div>
                  <p className="text-xs text-zinc-600">
                    Syncs tasks from the default space configured in Settings. Data is normalized and fed into risk analysis.
                  </p>
                </div>
              ) : (
                <div className="text-center py-8">
                  <ListChecks className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
                  <p className="text-zinc-400">ClickUp not configured</p>
                  <Button variant="outline" className="mt-4 border-white/10" onClick={() => window.location.href = '/settings'}>
                    Configure ClickUp
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sheets" className="space-y-6">
          <Card className="bg-zinc-900/50 border-white/10">
            <CardHeader className="border-b border-white/10">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white">Google Sheets Import</CardTitle>
                  <CardDescription className="text-zinc-500">Import data with flexible column mapping</CardDescription>
                </div>
                {sheetsConnected ? (
                  <Badge className="bg-emerald-500/20 text-emerald-400">Connected</Badge>
                ) : (
                  <Badge variant="outline" className="text-amber-500 border-amber-500/50">Not Connected</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {sheetsConnected ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="md:col-span-2 space-y-2">
                      <Label className="text-zinc-300">Google Sheets URL</Label>
                      <Input
                        value={sheetUrl}
                        onChange={(e) => setSheetUrl(e.target.value)}
                        placeholder="https://docs.google.com/spreadsheets/d/..."
                        className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                        data-testid="sheet-url-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-zinc-300">Sheet Name</Label>
                      <Input
                        value={sheetName}
                        onChange={(e) => setSheetName(e.target.value)}
                        placeholder="Sheet1"
                        className="bg-zinc-800 border-zinc-700 text-white"
                        data-testid="sheet-name-input"
                      />
                    </div>
                  </div>
                  <Button
                    onClick={handleSyncSheet}
                    disabled={syncingSheet || !sheetUrl || !selectedProject}
                    className="bg-emerald-600 hover:bg-emerald-700"
                    data-testid="sync-sheet-btn"
                  >
                    <RefreshCw className={cn("w-4 h-4 mr-2", syncingSheet && "animate-spin")} />
                    {syncingSheet ? 'Importing...' : 'Import Data'}
                  </Button>
                </div>
              ) : (
                <div className="text-center py-8">
                  <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
                  <p className="text-zinc-400">Google Sheets not connected</p>
                  <Button variant="outline" className="mt-4 border-white/10" onClick={() => window.location.href = '/settings'}>
                    Connect Google Sheets
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="upload" className="space-y-6">
          <Card className="bg-zinc-900/50 border-white/10">
            <CardHeader className="border-b border-white/10">
              <CardTitle className="text-white flex items-center gap-2">
                <Upload className="w-5 h-5 text-blue-500" />
                Upload Files
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div
                className={cn("upload-zone rounded-lg p-12 text-center cursor-pointer transition-all", dragOver && "drag-over")}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-input').click()}
                data-testid="upload-zone"
              >
                <input id="file-input" type="file" multiple accept=".json,.csv,.txt" className="hidden" onChange={handleFileSelect} data-testid="file-input" />
                <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-zinc-800 flex items-center justify-center">
                  <Upload className="w-8 h-8 text-zinc-500" />
                </div>
                <p className="text-white font-medium">{uploading ? 'Uploading...' : 'Drop files here or click to browse'}</p>
                <p className="text-sm text-zinc-500 mt-2 font-mono">Supports: .json, .csv, .txt</p>
              </div>

              {uploadedFiles.length > 0 && (
                <div className="mt-6 space-y-2">
                  <p className="text-sm text-zinc-400 mb-3">Uploaded Files:</p>
                  {uploadedFiles.map((file, i) => (
                    <div key={i} className={cn("flex items-center justify-between p-3 rounded-lg", file.status === 'success' ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-red-500/10 border border-red-500/20')}>
                      <div className="flex items-center gap-3">
                        <File className="w-5 h-5 text-zinc-400" />
                        <span className="text-sm text-white">{file.name}</span>
                        {file.records && <span className="text-xs text-zinc-500">{file.records} records</span>}
                      </div>
                      {file.status === 'success' ? <CheckCircle className="w-4 h-4 text-emerald-500" /> : <X className="w-4 h-4 text-red-500" />}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="manual" className="space-y-6">
          <Card className="bg-zinc-900/50 border-white/10">
            <CardHeader className="border-b border-white/10">
              <CardTitle className="text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-purple-500" />
                Manual Data Entry
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <form onSubmit={handleManualEntry} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label className="text-zinc-300">Entry Type</Label>
                    <Select value={entryType} onValueChange={setEntryType}>
                      <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white" data-testid="entry-type-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-zinc-800 border-zinc-700">
                        <SelectItem value="status_report" className="text-white hover:bg-zinc-700">Status Report</SelectItem>
                        <SelectItem value="meeting_notes" className="text-white hover:bg-zinc-700">Meeting Notes</SelectItem>
                        <SelectItem value="risk_register" className="text-white hover:bg-zinc-700">Risk Register Entry</SelectItem>
                        <SelectItem value="escalation" className="text-white hover:bg-zinc-700">Escalation</SelectItem>
                        <SelectItem value="incident" className="text-white hover:bg-zinc-700">Incident Report</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-zinc-300">Date</Label>
                    <Input type="date" value={entryDate} onChange={(e) => setEntryDate(e.target.value)} className="bg-zinc-800 border-zinc-700 text-white" data-testid="entry-date-input" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-zinc-300">Title *</Label>
                  <Input value={entryTitle} onChange={(e) => setEntryTitle(e.target.value)} placeholder="e.g., Weekly Status Update" required className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500" data-testid="entry-title-input" />
                </div>
                <div className="space-y-2">
                  <Label className="text-zinc-300">Content *</Label>
                  <Textarea value={entryContent} onChange={(e) => setEntryContent(e.target.value)} placeholder="Enter content..." required rows={8} className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500" data-testid="entry-content-input" />
                </div>
                <div className="flex justify-end">
                  <Button type="submit" disabled={submitting || !selectedProject} className="bg-white text-black hover:bg-zinc-200" data-testid="submit-entry-btn">
                    {submitting ? 'Saving...' : 'Save Entry'}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
