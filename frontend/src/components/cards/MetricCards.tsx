import React from 'react';
import type { KPIMetrics } from '../../hooks/useDashboardData';
import {
  Calendar, CheckCircle2, AlertTriangle, AlertCircle, Sparkles,
  Clock, FileText, FileCheck, FileX, Repeat2, Zap, ShieldCheck,
  ClipboardCheck, MessageSquare, AlertOctagon, CheckCheck, Hourglass
} from 'lucide-react';

interface MetricCardsProps {
  kpis: KPIMetrics | undefined;
  isLoading: boolean;
}

const Card: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  valueColor?: string;
  accent?: string;
  progress?: number;
  progressColor?: string;
  isCTA?: boolean;
}> = ({ title, value, subtitle, icon, valueColor = 'text-slate-800', accent = 'border-slate-200', progress, progressColor = 'bg-blue-500', isCTA }) => (
  <div className={`bg-white border ${accent} rounded-sm p-4 shadow-sm ${isCTA ? 'ring-1 ring-blue-200' : ''}`}>
    <div className="flex items-start justify-between mb-2">
      <div className="p-1.5 rounded bg-slate-50 border border-slate-100">{icon}</div>
    </div>
    <div className={`text-2xl font-bold tracking-tight ${valueColor} mb-0.5 leading-none`}>{value}</div>
    <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wide mb-1">{title}</div>
    {subtitle && <div className="text-[10px] text-slate-400">{subtitle}</div>}
    {typeof progress === 'number' && (
      <div className="mt-2 h-1 bg-slate-100 rounded-none overflow-hidden">
        <div className={`h-full ${progressColor}`} style={{ width: `${Math.min(progress, 100)}%` }} />
      </div>
    )}
  </div>
);

const SectionHeader: React.FC<{ icon: React.ReactNode; title: string; subtitle?: string; color?: string }> = ({
  icon, title, subtitle, color = 'text-slate-700'
}) => (
  <div className="flex items-center gap-2 mb-3">
    <div className={`${color}`}>{icon}</div>
    <div>
      <h3 className={`text-sm font-bold ${color}`}>{title}</h3>
      {subtitle && <p className="text-[10px] text-slate-400">{subtitle}</p>}
    </div>
    <div className="flex-1 h-px bg-slate-100 ml-2" />
  </div>
);

const ComingSoon: React.FC<{ label: string; icon: React.ReactNode }> = ({ label, icon }) => (
  <div className="bg-slate-50 border border-dashed border-slate-200 rounded-xl p-4 flex flex-col items-center justify-center text-center gap-2 opacity-70">
    <div className="text-slate-300">{icon}</div>
    <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">{label}</div>
    <div className="text-[10px] text-slate-400 italic">Coming Soon</div>
  </div>
);

export const MetricCards: React.FC<MetricCardsProps> = ({ kpis, isLoading }) => {
  if (isLoading || !kpis) {
    return (
      <div className="space-y-6">
        {[5, 5, 3, 3].map((n, si) => (
          <div key={si} className="space-y-2">
            <div className="h-5 bg-slate-200 rounded w-40" />
            <div className={`grid gap-3 grid-cols-2 md:grid-cols-${n}`}>
              {[...Array(n)].map((_, i) => <div key={i} className="bg-white border border-slate-200 rounded-xl h-24 shadow-sm" />)}
            </div>
          </div>
        ))}
      </div>
    );
  }

  const completionPct = kpis.completion_rate;
  const pendingPct = Math.max(0, 100 - completionPct);

  return (
    <div className="space-y-6">

      {/* ── Section 1: Survey Monitoring ── */}
      <div>
        <SectionHeader
          icon={<Calendar className="h-4 w-4" />}
          title="Survey Monitoring"
          subtitle="Based on Survey Status column"
          color="text-blue-700"
        />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <Card
            title="Total Surveys Scheduled"
            value={kpis.total_surveys_scheduled}
            icon={<Calendar className="h-4 w-4 text-blue-600" />}
            valueColor="text-slate-900"
            isCTA
          />
          <Card
            title="Completed"
            value={kpis.completed}
            subtitle={`${completionPct.toFixed(1)}% completion rate • ${kpis.total_surveyed_length.toLocaleString()} KM`}
            icon={<CheckCircle2 className="h-4 w-4 text-emerald-600" />}
            valueColor="text-emerald-700"
            accent="border-emerald-200"
            progress={completionPct}
            progressColor="bg-emerald-500"
          />
          <Card
            title="Pending"
            value={kpis.pending}
            subtitle={`${pendingPct.toFixed(1)}% not yet done`}
            icon={<Clock className="h-4 w-4 text-amber-500" />}
            valueColor="text-amber-700"
            accent="border-amber-200"
            progress={pendingPct}
            progressColor="bg-amber-500"
          />
          <Card
            title="Scheduled"
            value={kpis.scheduled}
            subtitle="Survey scheduled status"
            icon={<Calendar className="h-4 w-4 text-indigo-500" />}
            valueColor="text-indigo-700"
            accent="border-indigo-200"
          />
          <Card
            title="Cancelled"
            value={kpis.cancelled}
            subtitle="Surveys cancelled"
            icon={<FileX className="h-4 w-4 text-rose-500" />}
            valueColor={kpis.cancelled > 0 ? 'text-rose-700' : 'text-slate-400'}
            accent={kpis.cancelled > 0 ? 'border-rose-200' : 'border-slate-200'}
          />
        </div>
      </div>

      {/* ── Section 2: Report Submission ── */}
      <div>
        <SectionHeader
          icon={<FileText className="h-4 w-4" />}
          title="Report Submission"
          subtitle="Based on Report Submission Status column — independent from Survey Status"
          color="text-purple-700"
        />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <Card
            title="Reports Expected"
            value={kpis.reports_expected}
            subtitle="= Completed surveys"
            icon={<FileText className="h-4 w-4 text-purple-600" />}
            valueColor="text-purple-700"
          />
          <Card
            title="Reports Received"
            value={kpis.reports_received}
            subtitle="Actual date exists"
            icon={<FileCheck className="h-4 w-4 text-emerald-600" />}
            valueColor="text-emerald-700"
            accent="border-emerald-200"
          />
          <Card
            title="Reports On Time"
            value={kpis.reports_on_time}
            subtitle="Status = On Time"
            icon={<CheckCheck className="h-4 w-4 text-emerald-500" />}
            valueColor="text-emerald-700"
            accent="border-emerald-200"
          />
          <Card
            title="Reports Delayed"
            value={kpis.reports_delayed}
            subtitle="Status = Delayed or D1/D2 > 0"
            icon={<AlertTriangle className="h-4 w-4 text-rose-500" />}
            valueColor={kpis.reports_delayed > 0 ? 'text-rose-700' : 'text-slate-400'}
            accent={kpis.reports_delayed > 0 ? 'border-rose-200' : 'border-slate-200'}
          />
          <Card
            title="Pending Reports"
            value={Math.max(0, kpis.reports_expected - kpis.reports_received)}
            subtitle="Expected but not yet received"
            icon={<Hourglass className="h-4 w-4 text-amber-500" />}
            valueColor="text-amber-700"
            accent="border-amber-200"
          />
        </div>
      </div>

      {/* ── Section 3: Quality & Defects ── */}
      <div>
        <SectionHeader
          icon={<Sparkles className="h-4 w-4" />}
          title="Quality & Defect Analytics"
          subtitle="Precision/Recall and defect tracking — N/A if columns are empty in spreadsheet"
          color="text-indigo-700"
        />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Precision */}
          {kpis.average_precision !== null ? (
            <Card
              title="Avg Precision"
              value={`${(kpis.average_precision * 100).toFixed(1)}%`}
              subtitle="Mean precision score"
              icon={<Sparkles className="h-4 w-4 text-indigo-500" />}
              valueColor="text-indigo-700"
              accent="border-indigo-200"
              progress={kpis.average_precision * 100}
              progressColor="bg-indigo-500"
            />
          ) : <ComingSoon label="Avg Precision" icon={<Sparkles className="h-6 w-6" />} />}

          {/* Recall */}
          {kpis.average_recall !== null ? (
            <Card
              title="Avg Recall"
              value={`${(kpis.average_recall * 100).toFixed(1)}%`}
              subtitle="Mean recall score"
              icon={<Zap className="h-4 w-4 text-cyan-500" />}
              valueColor="text-cyan-700"
              accent="border-cyan-200"
              progress={kpis.average_recall * 100}
              progressColor="bg-cyan-500"
            />
          ) : <ComingSoon label="Avg Recall" icon={<Zap className="h-6 w-6" />} />}

          {/* Defects Total */}
          {kpis.defects_total !== null ? (
            <Card
              title="Total Defects"
              value={kpis.defects_total}
              subtitle="All defects reported"
              icon={<AlertOctagon className="h-4 w-4 text-orange-500" />}
              valueColor="text-orange-700"
              accent="border-orange-200"
            />
          ) : <ComingSoon label="Total Defects" icon={<AlertOctagon className="h-6 w-6" />} />}

          {/* Repeated Defects */}
          {kpis.defects_repeated !== null ? (
            <Card
              title="Repeated Defects"
              value={kpis.defects_repeated}
              subtitle="From previous cycles"
              icon={<Repeat2 className="h-4 w-4 text-rose-500" />}
              valueColor="text-rose-700"
              accent="border-rose-200"
            />
          ) : <ComingSoon label="Repeated Defects" icon={<Repeat2 className="h-6 w-6" />} />}

          {/* New Defects */}
          {kpis.defects_new !== null ? (
            <Card
              title="New Defects"
              value={kpis.defects_new}
              subtitle="= Total − Repeated"
              icon={<AlertCircle className="h-4 w-4 text-amber-500" />}
              valueColor="text-amber-700"
              accent="border-amber-200"
            />
          ) : <ComingSoon label="New Defects" icon={<AlertCircle className="h-6 w-6" />} />}

          {/* Discrepancies */}
          {kpis.discrepancies_raised !== null ? (
            <Card
              title="Discrepancies"
              value={kpis.discrepancies_raised}
              subtitle={`${kpis.discrepancies_pending ?? 0} pending resolution`}
              icon={<AlertTriangle className="h-4 w-4 text-purple-500" />}
              valueColor="text-purple-700"
              accent="border-purple-200"
            />
          ) : <ComingSoon label="Discrepancies" icon={<AlertTriangle className="h-6 w-6" />} />}
        </div>
      </div>

      {/* ── Section 4: Validation ── */}
      {(kpis.reports_validated !== null || kpis.piu_communication_completed !== null) && (
        <div>
          <SectionHeader
            icon={<ShieldCheck className="h-4 w-4" />}
            title="Report Validation"
            subtitle="Based on Report Validation Date and PIU Communication Date columns"
            color="text-teal-700"
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <Card
              title="Reports Validated"
              value={kpis.reports_validated ?? 'N/A'}
              subtitle="Validation date exists"
              icon={<ClipboardCheck className="h-4 w-4 text-teal-600" />}
              valueColor="text-teal-700"
              accent="border-teal-200"
            />
            <Card
              title="Pending Validation"
              value={kpis.reports_pending_validation ?? 'N/A'}
              subtitle="Received but not yet validated"
              icon={<Hourglass className="h-4 w-4 text-amber-500" />}
              valueColor="text-amber-700"
              accent="border-amber-200"
            />
            <Card
              title="PIU Communicated"
              value={kpis.piu_communication_completed ?? 'N/A'}
              subtitle="Interim acceptance date exists"
              icon={<MessageSquare className="h-4 w-4 text-blue-500" />}
              valueColor="text-blue-700"
              accent="border-blue-200"
            />
            <Card
              title="Pending PIU Comm."
              value={kpis.piu_communication_pending ?? 'N/A'}
              subtitle="Received but not communicated"
              icon={<AlertCircle className="h-4 w-4 text-rose-500" />}
              valueColor="text-rose-700"
              accent="border-rose-200"
            />
          </div>
        </div>
      )}

    </div>
  );
};
