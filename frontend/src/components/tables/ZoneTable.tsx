import React from 'react';
import type { ZoneTableRow } from '../../hooks/useDashboardData';
import { Map, ArrowRight } from 'lucide-react';

interface ZoneTableProps {
  data: ZoneTableRow[] | undefined;
  isLoading: boolean;
  selectedZone: string | null;
  onSelectZone: (zone: string) => void;
}

export const ZoneTable: React.FC<ZoneTableProps> = ({
  data,
  isLoading,
  selectedZone,
  onSelectZone,
}) => {
  if (isLoading) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm animate-pulse">
        <div className="h-6 bg-slate-200 rounded w-1/4 mb-4" />
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-10 bg-slate-100 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-8 shadow-sm text-center">
        <Map className="h-12 w-12 text-slate-300 mx-auto mb-2" />
        <h3 className="text-slate-600 font-semibold text-sm">No Regional Office / Zone Data Available</h3>
        <p className="text-slate-400 text-xs mt-1">Try broadening your search or filters.</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden print-card">
      <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between no-print">
        <div>
          <h3 className="font-bold text-slate-800 text-sm flex items-center space-x-2">
            <Map className="h-4.5 w-4.5 text-nhai-blue" />
            <span>National Highway Zones Comparison</span>
          </h3>
          <p className="text-slate-400 text-[11px] mt-0.5">Click any zone below to drill down into Regional Offices (ROs)</p>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-100 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              <th className="py-2 px-4 font-semibold border-r border-slate-200" rowSpan={2}>Zone</th>
              <th className="py-2 px-3 font-semibold text-center border-r border-slate-200 text-blue-700 bg-blue-50/50" colSpan={4}>Survey Metrics</th>
              <th className="py-2 px-3 font-semibold text-center text-purple-700 bg-purple-50/50" colSpan={5}>Report Metrics</th>
            </tr>
            <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              {/* Survey */}
              <th className="py-2 px-2 font-semibold text-center bg-blue-50/30">Scheduled</th>
              <th className="py-2 px-2 font-semibold text-center bg-blue-50/30">Completed</th>
              <th className="py-2 px-2 font-semibold text-center bg-blue-50/30">Pending</th>
              <th className="py-2 px-2 font-semibold border-r border-slate-200 bg-blue-50/30 text-right pr-4">Complete %</th>
              {/* Report */}
              <th className="py-2 px-2 font-semibold text-center bg-purple-50/30">Received</th>
              <th className="py-2 px-2 font-semibold text-center bg-purple-50/30">On Time</th>
              <th className="py-2 px-2 font-semibold text-center bg-purple-50/30">Delayed</th>
              {/* <th className="py-2 px-2 font-semibold text-center bg-purple-50/30">Validated</th> */}
              {/* <th className="py-2 px-2 font-semibold text-center bg-purple-50/30">Pend. Val.</th> */}
              <th className="py-2 px-2 font-semibold text-center bg-purple-50/30">Discrep.</th>
              <th className="py-2 px-4 font-semibold text-right bg-purple-50/30">Avg Delay</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-150">
            {[...data].sort((a,b)=> a.zone.localeCompare(b.zone)).map((row)=> {
              const isSelected = selectedZone === row.zone;
              return (
                <tr
                  key={row.zone}
                  onClick={() => onSelectZone(row.zone)}
                  className={`cursor-pointer hover:bg-slate-50 transition-colors duration-150 group ${isSelected ? 'bg-nhai-blue/5 border-l-4 border-l-nhai-orange' : ''}`}
                >
                  <td className="py-3 px-4 font-semibold text-slate-900 flex items-center justify-between border-r border-slate-100">
                    <span>{row.zone} Zone</span>
                    <ArrowRight className="h-3.5 w-3.5 text-slate-400 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition no-print" />
                  </td>
                  
                  {/* Survey */}
                  <td className="py-3 px-2 text-center font-medium text-slate-700">{row.scheduled}</td>
                  <td className="py-3 px-2 text-center font-semibold text-emerald-600">{row.completed}</td>
                  <td className="py-3 px-2 text-center font-medium text-amber-600">{row.pending}</td>
                  <td className="py-3 px-2 border-r border-slate-100">
                    <div className="flex items-center justify-end space-x-2 pr-2">
                      <span className="font-bold text-slate-800 text-right">{row.completion_rate}%</span>
                    </div>
                  </td>
                  
                  {/* Report */}
                  <td className="py-3 px-2 text-center font-semibold text-slate-800">{row.reports_received}</td>
                  <td className="py-3 px-2 text-center font-medium text-emerald-600">{row.on_time}</td>
                  <td className="py-3 px-2 text-center font-medium text-rose-600">{row.delayed}</td>
                  {/* <td className="py-3 px-2 text-center font-medium text-teal-600">{row.reports_validated ?? 'N/A'}</td> */}
                  {/* <td className="py-3 px-2 text-center font-medium text-amber-600">{row.pending_validation ?? 'N/A'}</td> */}
                  <td className="py-3 px-2 text-center font-medium text-purple-600">{row.discrepancies ?? 'N/A'}</td>
                  
                  <td className="py-3 px-4 text-right font-mono text-slate-600">
                    {row.average_delay > 0 ? `${row.average_delay}d` : '-'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
