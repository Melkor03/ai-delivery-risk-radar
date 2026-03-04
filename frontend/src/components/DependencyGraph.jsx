// DependencyGraph.jsx - Task dependency visualization
import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  GitBranch, 
  AlertTriangle, 
  ExternalLink,
  ZoomIn,
  ZoomOut,
  Maximize2
} from 'lucide-react';
import { cn } from '@/lib/utils';

const getRiskColor = (level) => {
  switch (level) {
    case 'HIGH': return '#ef4444';
    case 'MEDIUM': return '#f59e0b';
    case 'LOW': return '#10b981';
    default: return '#6b7280';
  }
};

const getStatusColor = (status) => {
  const s = (status || '').toLowerCase();
  if (['complete', 'done', 'closed', 'resolved'].includes(s)) return '#10b981';
  if (['in progress', 'in review', 'review', 'doing'].includes(s)) return '#3b82f6';
  if (['blocked'].includes(s)) return '#7c3aed';
  return '#6b7280';
};

// Simple force-directed layout simulation
const simulateForceLayout = (nodes, edges, width, height) => {
  const positioned = nodes.map((node, i) => ({
    ...node,
    x: width / 2 + (Math.random() - 0.5) * width * 0.6,
    y: height / 2 + (Math.random() - 0.5) * height * 0.6,
    vx: 0,
    vy: 0
  }));

  const nodeMap = {};
  positioned.forEach(n => nodeMap[n.id] = n);

  // Simple force simulation
  for (let i = 0; i < 100; i++) {
    // Repulsion between all nodes
    for (let j = 0; j < positioned.length; j++) {
      for (let k = j + 1; k < positioned.length; k++) {
        const dx = positioned[k].x - positioned[j].x;
        const dy = positioned[k].y - positioned[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = 5000 / (dist * dist);
        
        positioned[j].vx -= (dx / dist) * force;
        positioned[j].vy -= (dy / dist) * force;
        positioned[k].vx += (dx / dist) * force;
        positioned[k].vy += (dy / dist) * force;
      }
    }

    // Attraction along edges
    edges.forEach(edge => {
      const source = nodeMap[edge.from];
      const target = nodeMap[edge.to];
      if (source && target) {
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = dist * 0.01;
        
        source.vx += (dx / dist) * force;
        source.vy += (dy / dist) * force;
        target.vx -= (dx / dist) * force;
        target.vy -= (dy / dist) * force;
      }
    });

    // Apply velocities with damping
    positioned.forEach(node => {
      node.x += node.vx * 0.1;
      node.y += node.vy * 0.1;
      node.vx *= 0.9;
      node.vy *= 0.9;
      
      // Keep within bounds
      node.x = Math.max(60, Math.min(width - 60, node.x));
      node.y = Math.max(40, Math.min(height - 40, node.y));
    });
  }

  return positioned;
};

export default function DependencyGraph({ data, loading = false }) {
  const svgRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState(null);
  const [positions, setPositions] = useState([]);

  const width = 800;
  const height = 500;

  useEffect(() => {
    if (data?.nodes && data.nodes.length > 0) {
      const positioned = simulateForceLayout(data.nodes, data.edges || [], width, height);
      setPositions(positioned);
    }
  }, [data]);

  if (loading) {
    return (
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <GitBranch className="w-5 h-5 text-purple-500" />
            Task Dependencies
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-96 bg-zinc-800/50 rounded-lg animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <Card className="bg-zinc-900/50 border-white/10">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <GitBranch className="w-5 h-5 text-purple-500" />
            Task Dependencies
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center text-zinc-400">
            <div className="text-center">
              <GitBranch className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No dependency data available.</p>
              <p className="text-sm text-zinc-500 mt-1">Dependencies are extracted from ClickUp task links.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const { edges = [], blocked_chains = [] } = data;
  const nodeMap = {};
  positions.forEach(n => nodeMap[n.id] = n);

  return (
    <Card className="bg-zinc-900/50 border-white/10">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-white">
            <GitBranch className="w-5 h-5 text-purple-500" />
            Task Dependencies
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-zinc-400 border-zinc-700">
              {edges.length} dependencies
            </Badge>
            {data.blocked_count > 0 && (
              <Badge variant="outline" className="text-red-400 border-red-500/30 bg-red-500/10">
                {data.blocked_count} blocked
              </Badge>
            )}
            <div className="flex items-center gap-1 ml-2">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setZoom(z => Math.max(0.5, z - 0.1))}
              >
                <ZoomOut className="w-4 h-4" />
              </Button>
              <span className="text-xs text-zinc-500 w-12 text-center">{Math.round(zoom * 100)}%</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setZoom(z => Math.min(2, z + 0.1))}
              >
                <ZoomIn className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Blocked chains warning */}
        {blocked_chains.length > 0 && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span className="text-sm font-medium text-red-400">
                {blocked_chains.length} Blocking Dependency Chain(s)
              </span>
            </div>
            <div className="space-y-1">
              {blocked_chains.slice(0, 3).map((chain, i) => (
                <p key={i} className="text-xs text-zinc-300">
                  <span className="text-red-400">{chain.blocked_task}</span>
                  <span className="text-zinc-500"> blocked by </span>
                  <span className="text-yellow-400">{chain.blocking_task}</span>
                  <span className="text-zinc-500"> ({chain.blocking_status})</span>
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Graph SVG */}
        <div className="relative bg-zinc-800/50 rounded-lg overflow-hidden" style={{ height: 400 }}>
          <svg
            ref={svgRef}
            width="100%"
            height="100%"
            viewBox={`${-pan.x} ${-pan.y} ${width / zoom} ${height / zoom}`}
            className="cursor-move"
          >
            <defs>
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#6b7280" />
              </marker>
              <marker
                id="arrowhead-blocked"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#ef4444" />
              </marker>
            </defs>

            {/* Edges */}
            {edges.map((edge, i) => {
              const source = nodeMap[edge.from];
              const target = nodeMap[edge.to];
              if (!source || !target) return null;

              const isBlocked = target.blocked;
              
              return (
                <line
                  key={i}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={isBlocked ? '#ef4444' : '#4b5563'}
                  strokeWidth={isBlocked ? 2 : 1}
                  strokeDasharray={edge.type === 'waiting_on' ? '5,5' : undefined}
                  markerEnd={isBlocked ? 'url(#arrowhead-blocked)' : 'url(#arrowhead)'}
                  opacity={0.6}
                />
              );
            })}

            {/* Nodes */}
            {positions.map((node) => (
              <g 
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onClick={() => setSelectedNode(node)}
                className="cursor-pointer"
              >
                {/* Node circle */}
                <circle
                  r={node.blocked ? 20 : 16}
                  fill={node.blocked ? '#7c3aed' : getStatusColor(node.status)}
                  stroke={getRiskColor(node.risk_level)}
                  strokeWidth={3}
                  opacity={0.9}
                />
                
                {/* Blocked indicator */}
                {node.blocked && (
                  <text
                    textAnchor="middle"
                    dy="5"
                    fill="white"
                    fontSize="14"
                    fontWeight="bold"
                  >
                    !
                  </text>
                )}

                {/* Label */}
                <text
                  y={node.blocked ? 32 : 28}
                  textAnchor="middle"
                  fill="#d4d4d8"
                  fontSize="10"
                  className="pointer-events-none"
                >
                  {node.name.slice(0, 20)}
                  {node.name.length > 20 && '...'}
                </text>
              </g>
            ))}
          </svg>

          {/* Legend */}
          <div className="absolute bottom-2 left-2 flex items-center gap-4 text-xs text-zinc-400 bg-zinc-900/80 px-2 py-1 rounded">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span>Done</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <span>In Progress</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-purple-500" />
              <span>Blocked</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-gray-500" />
              <span>To Do</span>
            </div>
          </div>
        </div>

        {/* Selected node details */}
        {selectedNode && (
          <div className="mt-4 p-3 rounded-lg bg-zinc-800 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-white">{selectedNode.name}</h4>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs"
                onClick={() => setSelectedNode(null)}
              >
                Close
              </Button>
            </div>
            <div className="grid grid-cols-4 gap-4 text-xs">
              <div>
                <span className="text-zinc-500">Status</span>
                <p className="text-zinc-300">{selectedNode.status}</p>
              </div>
              <div>
                <span className="text-zinc-500">Risk</span>
                <p className={cn(
                  selectedNode.risk_level === 'HIGH' && 'text-red-400',
                  selectedNode.risk_level === 'MEDIUM' && 'text-yellow-400',
                  selectedNode.risk_level === 'LOW' && 'text-green-400'
                )}>
                  {selectedNode.risk_level} ({selectedNode.risk_score})
                </p>
              </div>
              <div>
                <span className="text-zinc-500">Assignee</span>
                <p className="text-zinc-300">{selectedNode.assignee}</p>
              </div>
              <div>
                <span className="text-zinc-500">Blocked</span>
                <p className={selectedNode.blocked ? 'text-red-400' : 'text-green-400'}>
                  {selectedNode.blocked ? 'Yes' : 'No'}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
