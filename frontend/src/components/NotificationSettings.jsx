// NotificationSettings.jsx - Configure Slack and Email alerts
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Bell, 
  MessageSquare, 
  Mail, 
  Save, 
  TestTube,
  CheckCircle2,
  AlertTriangle,
  Settings2
} from 'lucide-react';
import { toast } from 'sonner';
import api from '@/lib/api';
import { cn } from '@/lib/utils';

export default function NotificationSettings() {
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [config, setConfig] = useState({
    slack_enabled: false,
    slack_webhook: '',
    slack_channel: '#risk-alerts',
    email_enabled: false,
    email_recipients: '',
    digest_frequency: 'daily',
    alert_threshold: 50,
    alert_on_high_risk: true,
    alert_on_overdue: true,
    alert_on_blocked: true
  });

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await api.get('/settings/notifications');
      if (response.data) {
        setConfig(prev => ({ ...prev, ...response.data }));
      }
    } catch (error) {
      console.log('No notification config found');
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      await api.post('/settings/notifications', config);
      toast.success('Notification settings saved!');
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setLoading(false);
    }
  };

  const handleTestSlack = async () => {
    if (!config.slack_webhook) {
      toast.error('Please enter a Slack webhook URL first');
      return;
    }
    
    try {
      setTesting(true);
      await api.post('/notifications/test-slack', {
        webhook: config.slack_webhook
      });
      toast.success('Test message sent to Slack!');
    } catch (error) {
      toast.error('Failed to send test message');
    } finally {
      setTesting(false);
    }
  };

  const handleTestEmail = async () => {
    if (!config.email_recipients) {
      toast.error('Please enter email recipients first');
      return;
    }
    
    try {
      setTesting(true);
      await api.post('/notifications/test-email', {
        recipients: config.email_recipients
      });
      toast.success('Test email sent!');
    } catch (error) {
      toast.error('Failed to send test email');
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Slack Integration */}
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/10">
                <MessageSquare className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <CardTitle className="text-white">Slack Integration</CardTitle>
                <CardDescription className="text-zinc-400">
                  Get real-time risk alerts in your Slack channel
                </CardDescription>
              </div>
            </div>
            <Switch
              checked={config.slack_enabled}
              onCheckedChange={(checked) => setConfig(prev => ({ ...prev, slack_enabled: checked }))}
            />
          </div>
        </CardHeader>
        
        {config.slack_enabled && (
          <CardContent className="space-y-4 border-t border-white/5 pt-4">
            <div className="space-y-2">
              <Label className="text-zinc-300">Webhook URL</Label>
              <Input
                type="url"
                placeholder="https://hooks.slack.com/services/..."
                value={config.slack_webhook}
                onChange={(e) => setConfig(prev => ({ ...prev, slack_webhook: e.target.value }))}
                className="bg-zinc-800 border-zinc-700 text-white"
              />
              <p className="text-xs text-zinc-500">
                Create an incoming webhook in your Slack workspace settings
              </p>
            </div>
            
            <div className="space-y-2">
              <Label className="text-zinc-300">Channel</Label>
              <Input
                placeholder="#risk-alerts"
                value={config.slack_channel}
                onChange={(e) => setConfig(prev => ({ ...prev, slack_channel: e.target.value }))}
                className="bg-zinc-800 border-zinc-700 text-white"
              />
            </div>

            <Button 
              variant="outline" 
              onClick={handleTestSlack}
              disabled={testing || !config.slack_webhook}
              className="border-zinc-700 text-zinc-300"
            >
              <TestTube className="w-4 h-4 mr-2" />
              Send Test Message
            </Button>
          </CardContent>
        )}
      </Card>

      {/* Email Digest */}
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <Mail className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <CardTitle className="text-white">Email Digest</CardTitle>
                <CardDescription className="text-zinc-400">
                  Receive periodic risk summary reports via email
                </CardDescription>
              </div>
            </div>
            <Switch
              checked={config.email_enabled}
              onCheckedChange={(checked) => setConfig(prev => ({ ...prev, email_enabled: checked }))}
            />
          </div>
        </CardHeader>
        
        {config.email_enabled && (
          <CardContent className="space-y-4 border-t border-white/5 pt-4">
            <div className="space-y-2">
              <Label className="text-zinc-300">Recipients</Label>
              <Input
                type="text"
                placeholder="email1@company.com, email2@company.com"
                value={config.email_recipients}
                onChange={(e) => setConfig(prev => ({ ...prev, email_recipients: e.target.value }))}
                className="bg-zinc-800 border-zinc-700 text-white"
              />
              <p className="text-xs text-zinc-500">
                Comma-separated list of email addresses
              </p>
            </div>
            
            <div className="space-y-2">
              <Label className="text-zinc-300">Frequency</Label>
              <Select 
                value={config.digest_frequency}
                onValueChange={(value) => setConfig(prev => ({ ...prev, digest_frequency: value }))}
              >
                <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-zinc-800 border-zinc-700">
                  <SelectItem value="daily" className="text-white">Daily (9 AM)</SelectItem>
                  <SelectItem value="weekly" className="text-white">Weekly (Monday 9 AM)</SelectItem>
                  <SelectItem value="realtime" className="text-white">Real-time (on threshold breach)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button 
              variant="outline" 
              onClick={handleTestEmail}
              disabled={testing || !config.email_recipients}
              className="border-zinc-700 text-zinc-300"
            >
              <TestTube className="w-4 h-4 mr-2" />
              Send Test Email
            </Button>
          </CardContent>
        )}
      </Card>

      {/* Alert Thresholds */}
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-yellow-500/10">
              <Settings2 className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <CardTitle className="text-white">Alert Thresholds</CardTitle>
              <CardDescription className="text-zinc-400">
                Configure when to trigger alerts
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Risk Score Threshold */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-zinc-300">Risk Score Threshold</Label>
              <Badge variant="outline" className="text-zinc-400 border-zinc-700">
                {config.alert_threshold}%
              </Badge>
            </div>
            <Slider
              value={[config.alert_threshold]}
              onValueChange={([value]) => setConfig(prev => ({ ...prev, alert_threshold: value }))}
              min={20}
              max={80}
              step={5}
              className="py-2"
            />
            <p className="text-xs text-zinc-500">
              Alert when project risk score exceeds this threshold
            </p>
          </div>

          {/* Specific Triggers */}
          <div className="space-y-3">
            <Label className="text-zinc-300">Alert Triggers</Label>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-800/50">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  <span className="text-sm text-zinc-300">High risk tasks detected</span>
                </div>
                <Switch
                  checked={config.alert_on_high_risk}
                  onCheckedChange={(checked) => setConfig(prev => ({ ...prev, alert_on_high_risk: checked }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-800/50">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-400" />
                  <span className="text-sm text-zinc-300">Tasks become overdue</span>
                </div>
                <Switch
                  checked={config.alert_on_overdue}
                  onCheckedChange={(checked) => setConfig(prev => ({ ...prev, alert_on_overdue: checked }))}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-800/50">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-purple-400" />
                  <span className="text-sm text-zinc-300">Tasks blocked</span>
                </div>
                <Switch
                  checked={config.alert_on_blocked}
                  onCheckedChange={(checked) => setConfig(prev => ({ ...prev, alert_on_blocked: checked }))}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button 
          onClick={handleSave} 
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700"
        >
          <Save className="w-4 h-4 mr-2" />
          Save Settings
        </Button>
      </div>
    </div>
  );
}
