import React from 'react';
import type { ChartData } from '../../hooks/useDashboardData';
import {
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, AreaChart, Area
} from 'recharts';
import { BarChart3, PieChart as PieIcon, TrendingUp, AlertTriangle, Briefcase } from 'lucide-react';

interface DashboardChartsProps {
  data: ChartData | undefined;
  isLoading: boolean;
}

export const DashboardCharts: React.FC<DashboardChartsProps> = ({ data, isLoading }) => {
  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6 no-print">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white border border-slate-200 rounded-xl h-72 animate-pulse shadow-sm" />
        ))}
      </div>
    );
  }

  // Color constants
  const COLORS = {
    completed: '#0A2540',   // Navy
    pending: '#F26A36',     // Orange
    teal: '#0D9488',
    purple: '#7C3AED',
    rose: '#E11D48',
    indigo: '#4F46E5',
    grid: '#F1F5F9',
  };

  // Custom tooltips for nice styling
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white border border-slate-200 rounded-lg p-2.5 shadow-md text-xs font-semibold text-slate-700">
          {label && <p className="text-[10px] text-slate-400 uppercase mb-1">{label}</p>}
          {payload.map((p: any, idx: number) => (
            <div key={idx} className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color || p.fill }} />
              <span>{p.name}:</span>
              <span className="font-bold text-slate-900">
                {typeof p.value === 'number' && p.value % 1 !== 0 ? p.value.toFixed(3) : p.value}
                {p.name.includes('%') || p.name.includes('Rate') ? '%' : ''}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-6 mt-6">
      {/* Top Row: Completion Ratio & Delay Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Pie Chart: Completion Rate */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-5 shadow-sm print-card flex flex-col justify-between h-80">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-2 mb-2 no-print">
            <PieIcon className="h-4.5 w-4.5 text-nhai-blue" />
            <h3 className="font-bold text-slate-800 text-xs uppercase tracking-wider">Completion Ratio</h3>
          </div>
          <div className="flex-1 min-h-0 flex items-center justify-center relative">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={data.completion_pie}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  <Cell fill={COLORS.completed} />
                  <Cell fill={COLORS.pending} />
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend iconSize={10} iconType="circle" wrapperStyle={{ fontSize: '11px', fontWeight: 600 }} />
              </PieChart>
            </ResponsiveContainer>
            
            {/* Center rate indicator */}
            {data.completion_pie[0].value + data.completion_pie[1].value > 0 && (
              <div className="absolute flex flex-col items-center justify-center pointer-events-none mt-[-10px]">
                <span className="text-2xl font-extrabold text-slate-850">
                  {((data.completion_pie[0].value / (data.completion_pie[0].value + data.completion_pie[1].value)) * 100).toFixed(0)}%
                </span>
                <span className="text-[9px] uppercase font-bold text-slate-400">Completed</span>
              </div>
            )}
          </div>
        </div>

        {/* Delay Distribution */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-5 shadow-sm print-card flex flex-col justify-between h-80">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-2 mb-2 no-print">
            <AlertTriangle className="h-4.5 w-4.5 text-nhai-blue" />
            <h3 className="font-bold text-slate-800 text-xs uppercase tracking-wider">Report Submission Delay Distribution</h3>
          </div>
          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.delay_distribution} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={COLORS.grid} />
                <XAxis dataKey="range" tick={{ fill: '#64748B', fontSize: 10, fontWeight: 500 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748B', fontSize: 10, fontWeight: 500 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Surveys Count" fill={COLORS.pending} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Middle Row: Zone Comparison & Weekly Trend */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Zone comparison bar */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm print-card h-80 flex flex-col justify-between">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-2 mb-2 no-print">
            <BarChart3 className="h-4.5 w-4.5 text-nhai-blue" />
            <h3 className="font-bold text-slate-800 text-xs uppercase tracking-wider">Zone Comparison (Scheduled vs Completed)</h3>
          </div>
          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.zone_comparison} margin={{ top: 15, right: 10, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={COLORS.grid} />
                <XAxis dataKey="zone" tick={{ fill: '#64748B', fontSize: 10, fontWeight: 500 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748B', fontSize: 10, fontWeight: 500 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconSize={8} wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="scheduled" name="Scheduled" fill={COLORS.pending} radius={[4, 4, 0, 0]} maxBarSize={40} />
                <Bar dataKey="completed" name="Completed" fill={COLORS.completed} radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Weekly Trend line */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm print-card h-80 flex flex-col justify-between">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-2 mb-2 no-print">
            <TrendingUp className="h-4.5 w-4.5 text-nhai-blue" />
            <h3 className="font-bold text-slate-800 text-xs uppercase tracking-wider">Weekly Survey Completion Trend</h3>
          </div>
          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.weekly_trend} margin={{ top: 15, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorComp" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.teal} stopOpacity={0.2}/>
                    <stop offset="95%" stopColor={COLORS.teal} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={COLORS.grid} />
                <XAxis dataKey="week_label" tick={{ fill: '#64748B', fontSize: 9, fontWeight: 500 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748B', fontSize: 10, fontWeight: 500 }} axisLine={false} tickLine={false} unit="%" />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconSize={8} wrapperStyle={{ fontSize: '11px' }} />
                <Area type="monotone" dataKey="completion_rate" name="Completion Rate (%)" stroke={COLORS.teal} fillOpacity={1} fill="url(#colorComp)" strokeWidth={2.5} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom Row: Provider Performance */}
      {data.provider_performance && data.provider_performance.length > 0 && data.provider_performance.some(p => p.precision !== null && p.precision !== undefined && p.precision !== 0 && p.recall !== null && p.recall !== undefined && p.recall !== 0) && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm print-card h-84 flex flex-col justify-between">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-2 mb-2 no-print">
            <Briefcase className="h-4.5 w-4.5 text-nhai-blue" />
            <h3 className="font-bold text-slate-800 text-xs uppercase tracking-wider">DAS Provider Quality Scorecard (Avg. Precision vs Recall)</h3>
          </div>
          <div className="flex-grow min-h-0 mt-2">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={data.provider_performance} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={COLORS.grid} />
                <XAxis dataKey="provider" tick={{ fill: '#64748B', fontSize: 10, fontWeight: 500 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0.7, 1.0]} tick={{ fill: '#64748B', fontSize: 10, fontWeight: 500 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconSize={8} wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="precision" name="Avg Precision" fill={COLORS.indigo} radius={[4, 4, 0, 0]} maxBarSize={30} />
                <Bar dataKey="recall" name="Avg Recall" fill={COLORS.teal} radius={[4, 4, 0, 0]} maxBarSize={30} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};
