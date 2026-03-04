import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { getProjects, createProject, deleteProject } from '@/lib/api';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { 
  Plus, 
  FolderKanban, 
  Search,
  Trash2,
  ArrowRight,
  Users,
  Calendar
} from 'lucide-react';

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    team_lead: '',
    team_size: '',
    start_date: '',
    target_end_date: ''
  });

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await getProjects();
      setProjects(response.data);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
      toast.error('Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    try {
      await createProject({
        ...newProject,
        team_size: parseInt(newProject.team_size) || 0
      });
      toast.success('Project created successfully');
      setIsDialogOpen(false);
      setNewProject({ name: '', description: '', team_lead: '', team_size: '', start_date: '', target_end_date: '' });
      fetchProjects();
    } catch (error) {
      console.error('Failed to create project:', error);
      toast.error('Failed to create project');
    }
  };

  const handleDeleteProject = async (projectId, e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this project?')) return;
    
    try {
      await deleteProject(projectId);
      toast.success('Project deleted');
      fetchProjects();
    } catch (error) {
      console.error('Failed to delete project:', error);
      toast.error('Failed to delete project');
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

  const getRiskBg = (level) => {
    switch (level?.toUpperCase()) {
      case 'HIGH': return 'bg-red-500/10';
      case 'MEDIUM': return 'bg-amber-500/10';
      case 'LOW': return 'bg-emerald-500/10';
      default: return 'bg-zinc-500/10';
    }
  };

  const filteredProjects = projects.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.team_lead?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-zinc-800 rounded" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="h-48 bg-zinc-800 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="projects-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Projects</h1>
          <p className="text-zinc-500 mt-1">Manage and monitor your delivery projects</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-white text-black hover:bg-zinc-200" data-testid="create-project-btn">
              <Plus className="w-4 h-4 mr-2" />
              New Project
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-zinc-900 border-white/10">
            <DialogHeader>
              <DialogTitle className="text-white">Create New Project</DialogTitle>
              <DialogDescription className="text-zinc-400">
                Add a new project to monitor for delivery risks
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateProject} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label className="text-zinc-300">Project Name *</Label>
                <Input
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  placeholder="e.g., Platform Migration"
                  required
                  className="bg-zinc-800 border-zinc-700 text-white"
                  data-testid="project-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-zinc-300">Description</Label>
                <Textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  placeholder="Brief description of the project"
                  className="bg-zinc-800 border-zinc-700 text-white"
                  data-testid="project-description-input"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-zinc-300">Team Lead</Label>
                  <Input
                    value={newProject.team_lead}
                    onChange={(e) => setNewProject({ ...newProject, team_lead: e.target.value })}
                    placeholder="Lead name"
                    className="bg-zinc-800 border-zinc-700 text-white"
                    data-testid="project-lead-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-zinc-300">Team Size</Label>
                  <Input
                    type="number"
                    value={newProject.team_size}
                    onChange={(e) => setNewProject({ ...newProject, team_size: e.target.value })}
                    placeholder="0"
                    className="bg-zinc-800 border-zinc-700 text-white"
                    data-testid="project-size-input"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-zinc-300">Start Date</Label>
                  <Input
                    type="date"
                    value={newProject.start_date}
                    onChange={(e) => setNewProject({ ...newProject, start_date: e.target.value })}
                    className="bg-zinc-800 border-zinc-700 text-white"
                    data-testid="project-start-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-zinc-300">Target End Date</Label>
                  <Input
                    type="date"
                    value={newProject.target_end_date}
                    onChange={(e) => setNewProject({ ...newProject, target_end_date: e.target.value })}
                    className="bg-zinc-800 border-zinc-700 text-white"
                    data-testid="project-end-input"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="ghost" onClick={() => setIsDialogOpen(false)} className="text-zinc-400">
                  Cancel
                </Button>
                <Button type="submit" className="bg-white text-black hover:bg-zinc-200" data-testid="submit-project-btn">
                  Create Project
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
        <Input
          placeholder="Search projects..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10 bg-zinc-900 border-white/10 text-white placeholder:text-zinc-500"
          data-testid="search-projects-input"
        />
      </div>

      {/* Projects Grid */}
      {filteredProjects.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((project, i) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className={cn(
                "block animate-fade-in",
                `stagger-${(i % 5) + 1}`
              )}
              data-testid={`project-card-${project.id}`}
            >
              <Card className={cn(
                "bg-zinc-900/50 border-white/10 hover-lift h-full transition-all",
                project.risk_level === 'HIGH' && "tracing-beam"
              )}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center", getRiskBg(project.risk_level))}>
                      <FolderKanban className={cn("w-5 h-5", getRiskColor(project.risk_level).split(' ')[0])} />
                    </div>
                    <Badge variant="outline" className={cn("", getRiskColor(project.risk_level))}>
                      {project.risk_level || 'NEUTRAL'}
                    </Badge>
                  </div>
                  <CardTitle className="text-white mt-3 text-lg">{project.name}</CardTitle>
                  {project.description && (
                    <p className="text-sm text-zinc-500 line-clamp-2">{project.description}</p>
                  )}
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-4 text-zinc-500">
                      {project.team_lead && (
                        <span className="flex items-center gap-1">
                          <Users className="w-3 h-3" />
                          {project.team_lead}
                        </span>
                      )}
                      {project.target_end_date && (
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {new Date(project.target_end_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-zinc-400">{project.risk_score}%</span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-zinc-500 hover:text-red-500 hover:bg-red-500/10"
                        onClick={(e) => handleDeleteProject(project.id, e)}
                        data-testid={`delete-project-${project.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <Card className="bg-zinc-900/50 border-white/10">
          <CardContent className="py-12 text-center">
            <FolderKanban className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
            <p className="text-zinc-400">
              {searchQuery ? 'No projects match your search' : 'No projects yet'}
            </p>
            {!searchQuery && (
              <Button
                onClick={() => setIsDialogOpen(true)}
                className="mt-4 bg-white text-black hover:bg-zinc-200"
              >
                Create your first project
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
