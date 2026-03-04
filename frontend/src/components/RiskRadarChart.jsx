import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Legend, Tooltip } from 'recharts';

export const RiskRadarChart = ({ data }) => {
  if (!data) return null;

  const chartData = [
    { dimension: 'Scope Creep', value: data.scope_creep || 0, fullMark: 100 },
    { dimension: 'Dependencies', value: data.dependency_failure || 0, fullMark: 100 },
    { dimension: 'False Reporting', value: data.false_reporting || 0, fullMark: 100 },
    { dimension: 'Quality', value: data.quality_collapse || 0, fullMark: 100 },
    { dimension: 'Burnout', value: data.burnout || 0, fullMark: 100 },
    { dimension: 'Vendor Risk', value: data.vendor_risk || 0, fullMark: 100 },
  ];

  const getRiskColor = (value) => {
    if (value >= 70) return '#EF4444';
    if (value >= 40) return '#F59E0B';
    return '#10B981';
  };

  const avgRisk = Math.round(chartData.reduce((acc, d) => acc + d.value, 0) / chartData.length);
  const radarColor = getRiskColor(avgRisk);

  return (
    <div className="w-full h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={chartData}>
          <PolarGrid 
            stroke="rgba(255,255,255,0.1)" 
            gridType="polygon"
          />
          <PolarAngleAxis 
            dataKey="dimension" 
            tick={{ fill: '#A1A1AA', fontSize: 11 }}
            tickLine={{ stroke: 'rgba(255,255,255,0.1)' }}
          />
          <PolarRadiusAxis 
            angle={30} 
            domain={[0, 100]} 
            tick={{ fill: '#52525B', fontSize: 10 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
          />
          <Radar
            name="Risk Level"
            dataKey="value"
            stroke={radarColor}
            fill={radarColor}
            fillOpacity={0.3}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#18181B',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              color: '#F8FAFC'
            }}
            formatter={(value) => [`${value}%`, 'Risk']}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};
