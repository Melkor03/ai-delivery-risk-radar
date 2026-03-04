import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { saveJiraConfig, getJiraConfig, saveClickUpConfig, getClickUpConfig, testClickUpConnection, getClickUpTeams, getClickUpSpaces } from '@/lib/api';
import api from '@/lib/api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { 
  Settings, 
  Link as LinkIcon,
  Bell,
  Mail,
  MessageSquare,
  Save,
  ExternalLink,
  CheckCircle,
  RefreshCw,
  FileSpreadsheet,
  Table
} from 'lucide-react';

export default function SettingsPage() {
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState('integrations');
  
  // Jira state
  const [jiraConfig, setJiraConfig] = useState({
    instance_url: '',
    user_email: '',
    api_token: '',
    board_id: ''
  });
  const [savingJira, setSavingJira] = useState(false);
  const [jiraSaved, setJiraSaved] = useState(false);
  const [testingJira, setTestingJira] = useState(false);
  const [jiraConnected, setJiraConnected] = useState(false);
  const [jiraBoards, setJiraBoards] = useState([]);
  const [loadingBoards, setLoadingBoards] = useState(false);

  // Google Sheets state
  const [sheetsConfig, setSheetsConfig] = useState({
    client_id: '',
    client_secret: ''
  });
  const [savingSheets, setSavingSheets] = useState(false);
  const [sheetsConnected, setSheetsConnected] = useState(false);

  // ClickUp state
  const [clickupConfig, setClickupConfig] = useState({
    api_token: '',
    team_id: '',
    space_id: ''
  });
  const [savingClickUp, setSavingClickUp] = useState(false);
  const [clickupSaved, setClickupSaved] = useState(false);
  const [testingClickUp, setTestingClickUp] = useState(false);
  const [clickupConnected, setClickupConnected] = useState(false);
  const [clickupTeams, setClickupTeams] = useState([]);
  const [clickupSpaces, setClickupSpaces] = useState([]);
  const [loadingClickUpTeams, setLoadingClickUpTeams] = useState(false);

  // Notification preferences
  const [notifPrefs, setNotifPrefs] = useState({
    emailAlerts: true,
    slackAlerts: false,
    inAppAlerts: true,
    highRiskOnly: false
  });

  useEffect(() => {
    fetchJiraConfig();
    fetchSheetsStatus();
    fetchClickUpConfig();

    const savedPrefs = localStorage.getItem('notificationPrefs');
    if (savedPrefs) {
      setNotifPrefs(JSON.parse(savedPrefs));
    }

    // Check if redirected from Google OAuth
    if (searchParams.get('sheets_connected') === 'true') {
      toast.success('Google Sheets connected successfully!');
      setSheetsConnected(true);
    }
  }, [searchParams]);

  const fetchJiraConfig = async () => {
    try {
      const response = await getJiraConfig();
      if (response.data && Object.keys(response.data).length > 0) {
        setJiraConfig({
          instance_url: response.data.instance_url || '',
          user_email: response.data.user_email || '',
          api_token: '',
          board_id: response.data.board_id?.toString() || ''
        });
        setJiraSaved(true);
      }
    } catch (error) {
      console.error('Failed to fetch Jira config:', error);
    }
  };

  const fetchSheetsStatus = async () => {
    try {
      const response = await api.get('/oauth/sheets/status');
      setSheetsConnected(response.data.connected);
    } catch (error) {
      console.error('Failed to fetch Sheets status:', error);
    }
  };

  const handleSaveJira = async (e) => {
    e.preventDefault();
    setSavingJira(true);
    try {
      await saveJiraConfig({
        ...jiraConfig,
        board_id: jiraConfig.board_id ? parseInt(jiraConfig.board_id) : null
      });
      toast.success('Jira configuration saved');
      setJiraSaved(true);
    } catch (error) {
      console.error('Failed to save Jira config:', error);
      toast.error('Failed to save Jira configuration');
    } finally {
      setSavingJira(false);
    }
  };

  const handleTestJira = async () => {
    setTestingJira(true);
    try {
      const response = await api.post('/jira/test-connection');
      if (response.data.success) {
        toast.success(`Connected to ${response.data.server_title} (v${response.data.version})`);
        setJiraConnected(true);
        // Fetch boards
        await fetchJiraBoards();
      } else {
        toast.error(response.data.error || 'Connection failed');
        setJiraConnected(false);
      }
    } catch (error) {
      console.error('Jira test failed:', error);
      toast.error(error.response?.data?.detail || 'Connection test failed');
      setJiraConnected(false);
    } finally {
      setTestingJira(false);
    }
  };

  const fetchJiraBoards = async () => {
    setLoadingBoards(true);
    try {
      const response = await api.get('/jira/boards');
      setJiraBoards(response.data);
    } catch (error) {
      console.error('Failed to fetch boards:', error);
    } finally {
      setLoadingBoards(false);
    }
  };

  const handleSaveSheets = async (e) => {
    e.preventDefault();
    setSavingSheets(true);
    try {
      await api.post('/settings/google-sheets', sheetsConfig);
      toast.success('Google Sheets configuration saved');
    } catch (error) {
      console.error('Failed to save Sheets config:', error);
      toast.error('Failed to save configuration');
    } finally {
      setSavingSheets(false);
    }
  };

  const handleConnectSheets = async () => {
    try {
      const response = await api.get('/oauth/sheets/login');
      if (response.data.auth_url) {
        window.location.href = response.data.auth_url;
      }
    } catch (error) {
      console.error('Failed to start OAuth:', error);
      toast.error(error.response?.data?.detail || 'Failed to start authorization');
    }
  };

  // ClickUp handlers
  const fetchClickUpConfig = async () => {
    try {
      const response = await getClickUpConfig();
      if (response.data && Object.keys(response.data).length > 0) {
        setClickupConfig({
          api_token: '',
          team_id: response.data.team_id || '',
          space_id: response.data.space_id || ''
        });
        setClickupSaved(true);
      }
    } catch (error) {
      console.error('Failed to fetch ClickUp config:', error);
    }
  };

  const handleSaveClickUp = async (e) => {
    e.preventDefault();
    setSavingClickUp(true);
    try {
      await saveClickUpConfig(clickupConfig);
      toast.success('ClickUp configuration saved');
      setClickupSaved(true);
    } catch (error) {
      console.error('Failed to save ClickUp config:', error);
      toast.error('Failed to save ClickUp configuration');
    } finally {
      setSavingClickUp(false);
    }
  };

  const handleTestClickUp = async () => {
    setTestingClickUp(true);
    try {
      const response = await testClickUpConnection();
      if (response.data.success) {
        toast.success(`Connected as ${response.data.username || response.data.email}`);
        setClickupConnected(true);
        await fetchClickUpTeams();
      } else {
        toast.error(response.data.error || 'Connection failed');
        setClickupConnected(false);
      }
    } catch (error) {
      console.error('ClickUp test failed:', error);
      toast.error(error.response?.data?.detail || 'Connection test failed');
      setClickupConnected(false);
    } finally {
      setTestingClickUp(false);
    }
  };

  const fetchClickUpTeams = async () => {
    setLoadingClickUpTeams(true);
    try {
      const response = await getClickUpTeams();
      setClickupTeams(response.data);
      // Auto-select first team if none selected
      if (response.data.length > 0 && !clickupConfig.team_id) {
        const teamId = response.data[0].id;
        setClickupConfig(prev => ({ ...prev, team_id: teamId }));
        await fetchClickUpSpaces(teamId);
      } else if (clickupConfig.team_id) {
        await fetchClickUpSpaces(clickupConfig.team_id);
      }
    } catch (error) {
      console.error('Failed to fetch ClickUp teams:', error);
    } finally {
      setLoadingClickUpTeams(false);
    }
  };

  const fetchClickUpSpaces = async (teamId) => {
    try {
      const response = await getClickUpSpaces(teamId);
      setClickupSpaces(response.data);
    } catch (error) {
      console.error('Failed to fetch ClickUp spaces:', error);
    }
  };

  const handleClickUpTeamChange = async (teamId) => {
    setClickupConfig(prev => ({ ...prev, team_id: teamId, space_id: '' }));
    setClickupSpaces([]);
    await fetchClickUpSpaces(teamId);
  };

  const handleNotifPrefChange = (key, value) => {
    const newPrefs = { ...notifPrefs, [key]: value };
    setNotifPrefs(newPrefs);
    localStorage.setItem('notificationPrefs', JSON.stringify(newPrefs));
    toast.success('Preferences updated');
  };

  return (
    <div className="space-y-6" data-testid="settings-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
        <p className="text-zinc-500 mt-1">Configure integrations and notification preferences</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="bg-zinc-900 border border-white/10">
          <TabsTrigger value="integrations" className="data-[state=active]:bg-white data-[state=active]:text-black" data-testid="tab-integrations">
            <LinkIcon className="w-4 h-4 mr-2" />
            Integrations
          </TabsTrigger>
          <TabsTrigger value="notifications" className="data-[state=active]:bg-white data-[state=active]:text-black" data-testid="tab-notifications">
            <Bell className="w-4 h-4 mr-2" />
            Notifications
          </TabsTrigger>
        </TabsList>

        <TabsContent value="integrations" className="space-y-6">
          {/* Jira Integration */}
          <Card className="bg-zinc-900/50 border-white/10">
            <CardHeader className="border-b border-white/10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                    <svg className="w-6 h-6 text-blue-500" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M11.571 11.513H0a5.218 5.218 0 0 0 5.232 5.215h2.13v2.057A5.215 5.215 0 0 0 12.575 24V12.518a1.005 1.005 0 0 0-1.005-1.005z"/>
                      <path d="M5.23 5.226h11.57A5.218 5.218 0 0 0 11.57 0H5.23v5.226z"/>
                      <path d="M5.23 5.226H0v11.57a5.218 5.218 0 0 0 5.23-5.226V5.226z"/>
                    </svg>
                  </div>
                  <div>
                    <CardTitle className="text-white">Jira Integration</CardTitle>
                    <CardDescription className="text-zinc-500">
                      Sync sprint data, issues, and velocity metrics from Jira
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {jiraConnected && (
                    <Badge className="bg-emerald-500/20 text-emerald-400">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Connected
                    </Badge>
                  )}
                  {jiraSaved && !jiraConnected && (
                    <Badge variant="outline" className="text-amber-500 border-amber-500/50">
                      Configured
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              <form onSubmit={handleSaveJira} className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-zinc-300">Jira Instance URL *</Label>
                  <Input
                    value={jiraConfig.instance_url}
                    onChange={(e) => setJiraConfig({ ...jiraConfig, instance_url: e.target.value })}
                    placeholder="https://your-domain.atlassian.net"
                    required
                    className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                    data-testid="jira-url-input"
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-zinc-300">User Email *</Label>
                    <Input
                      type="email"
                      value={jiraConfig.user_email}
                      onChange={(e) => setJiraConfig({ ...jiraConfig, user_email: e.target.value })}
                      placeholder="your-email@company.com"
                      required
                      className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                      data-testid="jira-email-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-zinc-300">Default Board</Label>
                    {jiraBoards.length > 0 ? (
                      <Select 
                        value={jiraConfig.board_id} 
                        onValueChange={(v) => setJiraConfig({ ...jiraConfig, board_id: v })}
                      >
                        <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white" data-testid="jira-board-select">
                          <SelectValue placeholder="Select a board" />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-800 border-zinc-700">
                          {jiraBoards.map(board => (
                            <SelectItem key={board.id} value={board.id.toString()} className="text-white hover:bg-zinc-700">
                              {board.name} ({board.type})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        type="number"
                        value={jiraConfig.board_id}
                        onChange={(e) => setJiraConfig({ ...jiraConfig, board_id: e.target.value })}
                        placeholder="Board ID (optional)"
                        className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                        data-testid="jira-board-input"
                      />
                    )}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-zinc-300">API Token *</Label>
                  <Input
                    type="password"
                    value={jiraConfig.api_token}
                    onChange={(e) => setJiraConfig({ ...jiraConfig, api_token: e.target.value })}
                    placeholder={jiraSaved ? "••••••••••••••••" : "Enter your Jira API token"}
                    required={!jiraSaved}
                    className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                    data-testid="jira-token-input"
                  />
                  <p className="text-xs text-zinc-600 flex items-center gap-1">
                    <ExternalLink className="w-3 h-3" />
                    <a 
                      href="https://id.atlassian.com/manage-profile/security/api-tokens" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="hover:text-blue-400 transition-colors"
                    >
                      Generate API token from Atlassian
                    </a>
                  </p>
                </div>
                <div className="flex justify-between pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleTestJira}
                    disabled={testingJira || !jiraConfig.instance_url || !jiraConfig.user_email}
                    className="border-white/10 hover:bg-white/5"
                    data-testid="test-jira-btn"
                  >
                    <RefreshCw className={cn("w-4 h-4 mr-2", testingJira && "animate-spin")} />
                    {testingJira ? 'Testing...' : 'Test Connection'}
                  </Button>
                  <Button 
                    type="submit" 
                    disabled={savingJira}
                    className="bg-white text-black hover:bg-zinc-200"
                    data-testid="save-jira-btn"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    {savingJira ? 'Saving...' : 'Save Configuration'}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Google Sheets Integration */}
          <Card className="bg-zinc-900/50 border-white/10">
            <CardHeader className="border-b border-white/10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                    <FileSpreadsheet className="w-5 h-5 text-emerald-500" />
                  </div>
                  <div>
                    <CardTitle className="text-white">Google Sheets Integration</CardTitle>
                    <CardDescription className="text-zinc-500">
                      Import data from Google Sheets with flexible column mapping
                    </CardDescription>
                  </div>
                </div>
                {sheetsConnected && (
                  <Badge className="bg-emerald-500/20 text-emerald-400">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    Connected
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-6">
              {!sheetsConnected ? (
                <form onSubmit={handleSaveSheets} className="space-y-4">
                  <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20 mb-4">
                    <h4 className="text-sm font-medium text-blue-400 mb-2">Setup Instructions</h4>
                    <ol className="text-xs text-zinc-400 space-y-1 list-decimal list-inside">
                      <li>Go to Google Cloud Console and create a project</li>
                      <li>Enable Google Sheets API</li>
                      <li>Create OAuth credentials (Web application type)</li>
                      <li>Add redirect URI: <code className="text-blue-400">{window.location.origin}/api/oauth/sheets/callback</code></li>
                      <li>Enter your Client ID and Secret below</li>
                    </ol>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-zinc-300">Client ID</Label>
                      <Input
                        value={sheetsConfig.client_id}
                        onChange={(e) => setSheetsConfig({ ...sheetsConfig, client_id: e.target.value })}
                        placeholder="Your Google OAuth Client ID"
                        className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                        data-testid="sheets-client-id-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-zinc-300">Client Secret</Label>
                      <Input
                        type="password"
                        value={sheetsConfig.client_secret}
                        onChange={(e) => setSheetsConfig({ ...sheetsConfig, client_secret: e.target.value })}
                        placeholder="Your Google OAuth Client Secret"
                        className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                        data-testid="sheets-secret-input"
                      />
                    </div>
                  </div>
                  <div className="flex justify-between pt-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleConnectSheets}
                      disabled={!sheetsConfig.client_id || !sheetsConfig.client_secret}
                      className="border-white/10 hover:bg-white/5"
                      data-testid="connect-sheets-btn"
                    >
                      Connect Google Account
                    </Button>
                    <Button 
                      type="submit" 
                      disabled={savingSheets}
                      className="bg-white text-black hover:bg-zinc-200"
                      data-testid="save-sheets-btn"
                    >
                      <Save className="w-4 h-4 mr-2" />
                      {savingSheets ? 'Saving...' : 'Save Configuration'}
                    </Button>
                  </div>
                </form>
              ) : (
                <div className="text-center py-6">
                  <CheckCircle className="w-12 h-12 mx-auto mb-3 text-emerald-500" />
                  <p className="text-white font-medium">Google Sheets Connected</p>
                  <p className="text-sm text-zinc-500 mt-1">
                    You can now import data from Google Sheets in the Data Upload page
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* ClickUp Integration */}
          <Card className="bg-zinc-900/50 border-white/10">
            <CardHeader className="border-b border-white/10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center">
                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none">
                      <path d="M12 2L6 8.5L12 6L18 8.5L12 2Z" fill="#7B68EE"/>
                      <path d="M12 6L6 8.5V15.5L12 22L18 15.5V8.5L12 6Z" fill="#49CCF9" fillOpacity="0.8"/>
                      <path d="M12 6L6 8.5V15.5L12 12V6Z" fill="#FF02F0" fillOpacity="0.6"/>
                      <path d="M12 6L18 8.5V15.5L12 12V6Z" fill="#7B68EE" fillOpacity="0.6"/>
                    </svg>
                  </div>
                  <div>
                    <CardTitle className="text-white">ClickUp Integration</CardTitle>
                    <CardDescription className="text-zinc-500">
                      Sync tasks, lists, and custom fields from ClickUp
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {clickupConnected && (
                    <Badge className="bg-emerald-500/20 text-emerald-400">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Connected
                    </Badge>
                  )}
                  {clickupSaved && !clickupConnected && (
                    <Badge variant="outline" className="text-amber-500 border-amber-500/50">
                      Configured
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              <form onSubmit={handleSaveClickUp} className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-zinc-300">API Token *</Label>
                  <Input
                    type="password"
                    value={clickupConfig.api_token}
                    onChange={(e) => setClickupConfig({ ...clickupConfig, api_token: e.target.value })}
                    placeholder={clickupSaved ? "••••••••••••••••" : "Enter your ClickUp API token"}
                    required={!clickupSaved}
                    className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                    data-testid="clickup-token-input"
                  />
                  <p className="text-xs text-zinc-600 flex items-center gap-1">
                    <ExternalLink className="w-3 h-3" />
                    <a
                      href="https://app.clickup.com/settings/apps"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-purple-400 transition-colors"
                    >
                      Generate API token from ClickUp Settings
                    </a>
                  </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-zinc-300">Workspace (Team)</Label>
                    {clickupTeams.length > 0 ? (
                      <Select
                        value={clickupConfig.team_id}
                        onValueChange={handleClickUpTeamChange}
                      >
                        <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white" data-testid="clickup-team-select">
                          <SelectValue placeholder="Select a workspace" />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-800 border-zinc-700">
                          {clickupTeams.map(team => (
                            <SelectItem key={team.id} value={team.id} className="text-white hover:bg-zinc-700">
                              {team.name} ({team.members_count} members)
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        type="text"
                        value={clickupConfig.team_id}
                        onChange={(e) => setClickupConfig({ ...clickupConfig, team_id: e.target.value })}
                        placeholder="Team ID (test connection to load)"
                        className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                        data-testid="clickup-team-input"
                      />
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label className="text-zinc-300">Default Space</Label>
                    {clickupSpaces.length > 0 ? (
                      <Select
                        value={clickupConfig.space_id}
                        onValueChange={(v) => setClickupConfig({ ...clickupConfig, space_id: v })}
                      >
                        <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white" data-testid="clickup-space-select">
                          <SelectValue placeholder="Select a space" />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-800 border-zinc-700">
                          {clickupSpaces.map(space => (
                            <SelectItem key={space.id} value={space.id} className="text-white hover:bg-zinc-700">
                              {space.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        type="text"
                        value={clickupConfig.space_id}
                        onChange={(e) => setClickupConfig({ ...clickupConfig, space_id: e.target.value })}
                        placeholder="Space ID (optional)"
                        className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                        data-testid="clickup-space-input"
                      />
                    )}
                  </div>
                </div>
                <div className="flex justify-between pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleTestClickUp}
                    disabled={testingClickUp || !clickupConfig.api_token && !clickupSaved}
                    className="border-white/10 hover:bg-white/5"
                    data-testid="test-clickup-btn"
                  >
                    <RefreshCw className={cn("w-4 h-4 mr-2", testingClickUp && "animate-spin")} />
                    {testingClickUp ? 'Testing...' : 'Test Connection'}
                  </Button>
                  <Button
                    type="submit"
                    disabled={savingClickUp}
                    className="bg-white text-black hover:bg-zinc-200"
                    data-testid="save-clickup-btn"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    {savingClickUp ? 'Saving...' : 'Save Configuration'}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Slack - Coming Soon */}
          <Card className="bg-zinc-900/50 border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                    <MessageSquare className="w-5 h-5 text-purple-500" />
                  </div>
                  <div>
                    <p className="font-medium text-white">Slack Integration</p>
                    <p className="text-sm text-zinc-500">Send risk alerts to Slack channels</p>
                  </div>
                </div>
                <Badge variant="outline" className="text-zinc-500 border-zinc-600">Coming Soon</Badge>
              </div>
            </CardContent>
          </Card>

          {/* SendGrid - Coming Soon */}
          <Card className="bg-zinc-900/50 border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                    <Mail className="w-5 h-5 text-amber-500" />
                  </div>
                  <div>
                    <p className="font-medium text-white">Email Notifications (SendGrid)</p>
                    <p className="text-sm text-zinc-500">Send risk alerts via email</p>
                  </div>
                </div>
                <Badge variant="outline" className="text-zinc-500 border-zinc-600">Coming Soon</Badge>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications" className="space-y-6">
          <Card className="bg-zinc-900/50 border-white/10">
            <CardHeader className="border-b border-white/10">
              <CardTitle className="text-white flex items-center gap-2">
                <Bell className="w-5 h-5 text-blue-500" />
                Notification Preferences
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-white">In-App Notifications</p>
                  <p className="text-sm text-zinc-500">Show notifications within the dashboard</p>
                </div>
                <Switch
                  checked={notifPrefs.inAppAlerts}
                  onCheckedChange={(v) => handleNotifPrefChange('inAppAlerts', v)}
                  data-testid="toggle-inapp"
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-white">Email Alerts</p>
                  <p className="text-sm text-zinc-500">Receive risk alerts via email</p>
                </div>
                <Switch
                  checked={notifPrefs.emailAlerts}
                  onCheckedChange={(v) => handleNotifPrefChange('emailAlerts', v)}
                  data-testid="toggle-email"
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-white">Slack Notifications</p>
                  <p className="text-sm text-zinc-500">Send alerts to Slack channel</p>
                </div>
                <Switch
                  checked={notifPrefs.slackAlerts}
                  onCheckedChange={(v) => handleNotifPrefChange('slackAlerts', v)}
                  data-testid="toggle-slack"
                />
              </div>
              <div className="pt-4 border-t border-white/10">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-white">High Risk Only</p>
                    <p className="text-sm text-zinc-500">Only notify for high-risk alerts</p>
                  </div>
                  <Switch
                    checked={notifPrefs.highRiskOnly}
                    onCheckedChange={(v) => handleNotifPrefChange('highRiskOnly', v)}
                    data-testid="toggle-high-risk-only"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
