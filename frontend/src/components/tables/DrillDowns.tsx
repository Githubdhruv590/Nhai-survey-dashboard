import React from 'react';
import type { 
  ROTableRow, PIUTableRow, ProjectTableRow, SurveyRecordDetail 
} from '../../hooks/useDashboardData';
import { 
  MapPin, Folder, FileCheck, ArrowRight, ExternalLink, 
  CheckCircle2, Clock, AlertTriangle, AlertCircle
} from 'lucide-react';

interface DrillDownsProps {
  // Selections
  selectedZone: string | null;
  selectedRO: string | null;
  selectedPIU: string | null;
  selectedProject: string | null;
  selectedProjectName: string | null;
  
  // Handlers
  onSelectZone: (zone: string | null) => void;
  onSelectRO: (ro: string | null) => void;
  onSelectPIU: (piu: string | null) => void;
  onSelectProject: (upc: string | null, name: string | null) => void;
  
  // Data
  roData: ROTableRow[] | undefined;
  piuData: PIUTableRow[] | undefined;
  projectData: ProjectTableRow[] | undefined;
  surveyData: SurveyRecordDetail[] | undefined;
  
  // Loadings
  isLoadingRO: boolean;
  isLoadingPIU: boolean;
  isLoadingProject: boolean;
  isLoadingSurveys: boolean;
}

export const DrillDowns: React.FC<DrillDownsProps> = ({
  selectedZone,
  selectedRO,
  selectedPIU,
  selectedProject,
  selectedProjectName,
  onSelectZone,
  onSelectRO,
  onSelectPIU,
  onSelectProject,
  roData,
  piuData,
  projectData,
  surveyData,
  isLoadingRO,
  isLoadingPIU,
  isLoadingProject,
  isLoadingSurveys,
}) => {
  // If no Zone is selected, do not render drilldown
  if (!selectedZone) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 animate-slide-up print-card mt-6">
      {/* Breadcrumb Navigation */}
      <div className="flex flex-wrap items-center space-x-1.5 text-xs text-slate-400 font-semibold mb-5 bg-slate-50 px-3.5 py-2 rounded-lg border border-slate-100 no-print">
        <button 
          onClick={() => { onSelectZone(null); onSelectRO(null); onSelectPIU(null); onSelectProject(null, null); }} 
          className="hover:text-nhai-blue transition"
        >
          National
        </button>
        <ArrowRight className="h-3 w-3" />
        <button 
          onClick={() => { onSelectRO(null); onSelectPIU(null); onSelectProject(null, null); }}
          className={`hover:text-nhai-blue transition ${!selectedRO ? 'text-nhai-orange font-bold' : ''}`}
        >
          {selectedZone} Zone
        </button>
        
        {selectedRO && (
          <>
            <ArrowRight className="h-3 w-3" />
            <button 
              onClick={() => { onSelectPIU(null); onSelectProject(null, null); }}
              className={`hover:text-nhai-blue transition ${!selectedPIU ? 'text-nhai-orange font-bold' : ''}`}
            >
              {selectedRO}
            </button>
          </>
        )}

        {selectedPIU && (
          <>
            <ArrowRight className="h-3 w-3" />
            <button 
              onClick={() => onSelectProject(null, null)}
              className={`hover:text-nhai-blue transition ${!selectedProject ? 'text-nhai-orange font-bold' : ''}`}
            >
              {selectedPIU}
            </button>
          </>
        )}
        
        {selectedProject && (
          <>
            <ArrowRight className="h-3 w-3" />
            <span className="text-nhai-orange font-bold">
              UPC: {selectedProject} ({selectedProjectName})
            </span>
          </>
        )}
      </div>

      {/* LEVEL 1: RO Drilldown within selected Zone */}
      {selectedZone && !selectedRO && (
        <div>
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-800 flex items-center space-x-1.5">
              <MapPin className="h-4.5 w-4.5 text-nhai-blue" />
              <span>Regional Offices (ROs) in {selectedZone} Zone</span>
            </h3>
            <p className="text-slate-400 text-xs mt-0.5">Click an RO below to view its specific projects</p>
          </div>
          
          {isLoadingRO ? (
            <div className="space-y-2 py-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-10 bg-slate-50 rounded animate-pulse" />
              ))}
            </div>
          ) : roData && roData.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-2 px-3 border-r border-slate-200" rowSpan={2}>Regional Office</th>
                    <th className="py-2 px-3 font-semibold text-center border-r border-slate-200 text-blue-700 bg-blue-50/50" colSpan={4}>Survey Metrics</th>
                    <th className="py-2 px-3 font-semibold text-center text-purple-700 bg-purple-50/50" colSpan={7}>Report Metrics</th>
                  </tr>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-2 px-2 text-center bg-blue-50/30">Scheduled</th>
                    <th className="py-2 px-2 text-center bg-blue-50/30">Completed</th>
                    <th className="py-2 px-2 text-center bg-blue-50/30">Pending</th>
                    <th className="py-2 px-2 border-r border-slate-200 bg-blue-50/30 text-right pr-3">Complete %</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">Received</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">On Time</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">Delayed</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">Validated</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">Pend. Val.</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">Discrep.</th>
                    <th className="py-2 px-3 text-right bg-purple-50/30">Avg Delay</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {roData.map((row) => (
                    <tr 
                      key={row.ro_name}
                      onClick={() => onSelectRO(row.ro_name)}
                      className="cursor-pointer hover:bg-slate-50/80 transition-colors group"
                    >
                      <td className="py-3 px-3 font-semibold text-slate-800 flex items-center justify-between border-r border-slate-100">
                        <span>{row.ro_name}</span>
                        <ArrowRight className="h-3.5 w-3.5 text-slate-400 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition no-print" />
                      </td>
                      <td className="py-3 px-2 text-center text-slate-700">{row.scheduled}</td>
                      <td className="py-3 px-2 text-center font-semibold text-emerald-600">{row.completed}</td>
                      <td className="py-3 px-2 text-center text-amber-600">{row.pending}</td>
                      <td className="py-3 px-2 text-right font-bold text-slate-800 border-r border-slate-100 pr-3">{row.completion_rate}%</td>
                      <td className="py-3 px-2 text-center font-semibold text-slate-800">{row.reports_received}</td>
                      <td className="py-3 px-2 text-center font-medium text-emerald-600">{row.on_time}</td>
                      <td className="py-3 px-2 text-center font-medium text-rose-600">{row.delayed}</td>
                      <td className="py-3 px-2 text-center font-medium text-teal-600">{row.reports_validated ?? 'N/A'}</td>
                      <td className="py-3 px-2 text-center font-medium text-amber-600">{row.pending_validation ?? 'N/A'}</td>
                      <td className="py-3 px-2 text-center font-medium text-purple-600">{row.discrepancies ?? 'N/A'}</td>
                      <td className="py-3 px-3 text-right font-mono text-slate-600">
                        {row.average_delay > 0 ? `${row.average_delay}d` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-slate-400 italic text-xs py-4">No RO data available for this zone.</p>
          )}
        </div>
      )}

      {/* LEVEL 2: PIU Drilldown within selected RO */}
      {selectedRO && !selectedPIU && !selectedProject && (
        <div>
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-800 flex items-center space-x-1.5">
              <Folder className="h-4.5 w-4.5 text-nhai-blue" />
              <span>Project Implementation Units (PIUs) under {selectedRO}</span>
            </h3>
            <p className="text-slate-400 text-xs mt-0.5">Click a PIU below to view its specific projects</p>
          </div>
          
          {isLoadingPIU ? (
            <div className="space-y-2 py-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-10 bg-slate-50 rounded animate-pulse" />
              ))}
            </div>
          ) : piuData && piuData.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-2 px-3 border-r border-slate-200" rowSpan={2}>PIU Name</th>
                    <th className="py-2 px-3 font-semibold text-center border-r border-slate-200 text-blue-700 bg-blue-50/50" colSpan={4}>Survey Metrics</th>
                    <th className="py-2 px-3 font-semibold text-center text-purple-700 bg-purple-50/50" colSpan={7}>Report Metrics</th>
                  </tr>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-2 px-2 text-center bg-blue-50/30">Scheduled</th>
                    <th className="py-2 px-2 text-center bg-blue-50/30">Completed</th>
                    <th className="py-2 px-2 text-center bg-blue-50/30">Pending</th>
                    <th className="py-2 px-2 border-r border-slate-200 bg-blue-50/30 text-right pr-3">Complete %</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">Received</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">On Time</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">Delayed</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">Validated</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">Pend. Val.</th>
                    <th className="py-2 px-2 text-center bg-purple-50/30">Discrep.</th>
                    <th className="py-2 px-3 text-right bg-purple-50/30">Avg Delay</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {piuData.map((row) => (
                    <tr 
                      key={row.piu_name}
                      onClick={() => onSelectPIU(row.piu_name)}
                      className="cursor-pointer hover:bg-slate-50/80 transition-colors group"
                    >
                      <td className="py-3 px-3 font-semibold text-slate-800 flex items-center justify-between border-r border-slate-100">
                        <span>{row.piu_name}</span>
                        <ArrowRight className="h-3.5 w-3.5 text-slate-400 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition no-print" />
                      </td>
                      <td className="py-3 px-2 text-center text-slate-700">{row.scheduled}</td>
                      <td className="py-3 px-2 text-center font-semibold text-emerald-600">{row.completed}</td>
                      <td className="py-3 px-2 text-center text-amber-600">{row.pending}</td>
                      <td className="py-3 px-2 text-right font-bold text-slate-800 border-r border-slate-100 pr-3">{row.completion_rate}%</td>
                      <td className="py-3 px-2 text-center font-semibold text-slate-800">{row.reports_received}</td>
                      <td className="py-3 px-2 text-center font-medium text-emerald-600">{row.on_time}</td>
                      <td className="py-3 px-2 text-center font-medium text-rose-600">{row.delayed}</td>
                      <td className="py-3 px-2 text-center font-medium text-teal-600">{row.reports_validated ?? 'N/A'}</td>
                      <td className="py-3 px-2 text-center font-medium text-amber-600">{row.pending_validation ?? 'N/A'}</td>
                      <td className="py-3 px-2 text-center font-medium text-purple-600">{row.discrepancies ?? 'N/A'}</td>
                      <td className="py-3 px-3 text-right font-mono text-slate-600">
                        {row.average_delay > 0 ? `${row.average_delay}d` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-slate-400 italic text-xs py-4">No PIU data available for this RO.</p>
          )}
        </div>
      )}

      {/* LEVEL 3: Project Drilldown within selected PIU */}
      {selectedPIU && !selectedProject && (
        <div>
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-800 flex items-center space-x-1.5">
              <Folder className="h-4.5 w-4.5 text-nhai-blue" />
              <span>Projects under {selectedPIU}</span>
            </h3>
            <p className="text-slate-400 text-xs mt-0.5">Click a Project below to view all scheduled survey runs</p>
          </div>
          
          {isLoadingProject ? (
            <div className="space-y-2 py-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-10 bg-slate-55 rounded animate-pulse" />
              ))}
            </div>
          ) : projectData && projectData.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-2.5 px-3">UPC Code</th>
                    <th className="py-2.5 px-3">Project Name</th>
                    <th className="py-2.5 px-3">PIU Unit</th>
                    <th className="py-2.5 px-3 text-center">Scheduled</th>
                    <th className="py-2.5 px-3 text-center">Completed</th>
                    <th className="py-2.5 px-3 text-center">Pending</th>
                    <th className="py-2.5 px-3">Completion %</th>
                    <th className="py-2.5 px-3 text-center">Avg Precision</th>
                    <th className="py-2.5 px-3 text-center">Avg Recall</th>
                    <th className="py-2.5 px-3 text-right">Avg Delay</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {projectData.map((row) => (
                    <tr 
                      key={row.upc_code}
                      onClick={() => onSelectProject(row.upc_code, row.project_name)}
                      className="cursor-pointer hover:bg-slate-50/80 transition-colors group"
                    >
                      <td className="py-3 px-3 font-mono text-slate-650 font-bold">{row.upc_code}</td>
                      <td className="py-3 px-3 font-semibold text-slate-800 flex items-center justify-between">
                        <span>{row.project_name}</span>
                        <ArrowRight className="h-3.5 w-3.5 text-slate-400 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition no-print" />
                      </td>
                      <td className="py-3 px-3 text-slate-500 font-medium">{row.piu_name || row.ro_name}</td>
                      <td className="py-3 px-3 text-center text-slate-700">{row.scheduled}</td>
                      <td className="py-3 px-3 text-center font-semibold text-emerald-600">{row.completed}</td>
                      <td className="py-3 px-3 text-center text-slate-500">{row.pending}</td>
                      <td className="py-3 px-3 font-bold text-slate-800">{row.completion_rate}%</td>
                      <td className="py-3 px-3 text-center font-semibold text-indigo-650">
                        {row.precision != null && row.precision > 0 ? row.precision.toFixed(3) : '-'}
                      </td>
                      <td className="py-3 px-3 text-center font-semibold text-teal-650">
                        {row.recall != null && row.recall > 0 ? row.recall.toFixed(3) : '-'}
                      </td>
                      <td className="py-3 px-3 text-right font-semibold text-slate-850">
                        {row.average_delay > 0 ? `${row.average_delay}d` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-slate-400 italic text-xs py-4">No projects found for this RO.</p>
          )}
        </div>
      )}

      {/* LEVEL 4: Survey Runs list for selected Project */}
      {selectedProject && (
        <div>
          <div className="mb-5 flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-850 flex items-center space-x-1.5">
                <FileCheck className="h-4.5 w-4.5 text-nhai-blue" />
                <span>Survey Schedule History: {selectedProjectName}</span>
              </h3>
              <p className="text-slate-400 text-xs mt-0.5">UPC Code: {selectedProject} | Regional Office: {selectedRO}</p>
            </div>
            <button 
              onClick={() => onSelectProject(null, null)}
              className="text-xs font-semibold text-nhai-orange hover:text-nhai-orange-dark underline mt-2 sm:mt-0 no-print"
            >
              Back to Projects List
            </button>
          </div>
          
          {isLoadingSurveys ? (
            <div className="space-y-4 py-4">
              {[...Array(2)].map((_, i) => (
                <div key={i} className="h-28 bg-slate-50 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : surveyData && surveyData.length > 0 ? (
            <div className="space-y-4">
              {surveyData.map((survey) => {
                const status = survey.survey_status.toLowerCase();
                const isCompleted = status === 'completed';
                
                return (
                  <div 
                    key={survey.survey_id} 
                    className={`border rounded-xl p-4 shadow-sm transition-all duration-150 ${isCompleted ? 'border-slate-200 bg-white hover:shadow-md' : 'border-slate-100 bg-slate-50/50'}`}
                  >
                    {/* Header line */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-2.5 mb-3">
                      <div className="flex items-center space-x-2.5">
                        <span className="font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[10px] font-bold">
                          {survey.survey_id}
                        </span>
                        <div className="text-xs text-slate-500 font-medium">
                          Scheduled: <span className="font-semibold text-slate-700">{survey.scheduled_survey_date}</span>
                        </div>
                        {survey.actual_survey_date && (
                          <div className="text-xs text-slate-500 font-medium">
                            | Actual: <span className="font-semibold text-slate-750">{survey.actual_survey_date}</span>
                          </div>
                        )}
                      </div>
                      
                      {/* Badge status */}
                      <div className="flex items-center space-x-2">
                        {status === 'completed' && (
                          <span className="bg-emerald-50 text-emerald-700 border border-emerald-100 px-2.5 py-0.5 rounded-full text-[10px] font-bold flex items-center space-x-1">
                            <CheckCircle2 className="h-3 w-3" />
                            <span>Completed</span>
                          </span>
                        )}
                        {status === 'scheduled' && (
                          <span className="bg-blue-50 text-blue-700 border border-blue-100 px-2.5 py-0.5 rounded-full text-[10px] font-bold flex items-center space-x-1">
                            <Clock className="h-3 w-3" />
                            <span>Scheduled</span>
                          </span>
                        )}
                        {status !== 'completed' && status !== 'scheduled' && (
                          <span className="bg-amber-50 text-amber-700 border border-amber-100 px-2.5 py-0.5 rounded-full text-[10px] font-bold flex items-center space-x-1">
                            <AlertCircle className="h-3 w-3" />
                            <span>{survey.survey_status}</span>
                          </span>
                        )}
                      </div>
                    </div>
                    
                    {/* Content Section */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {/* Column 1: Road & Quantity Info */}
                      <div className="text-xs space-y-1 text-slate-500">
                        <div className="font-bold text-slate-800 mb-1.5 uppercase text-[9px] tracking-wider">Road Quantities</div>
                        <div>Main Carriageway Length: <span className="font-semibold text-slate-800">{survey.mcw_length_surveyed > 0 ? `${survey.mcw_length_surveyed} KM` : '-'}</span></div>
                        <div>Service Road Length: <span className="font-semibold text-slate-800">{survey.sr_length_surveyed > 0 ? `${survey.sr_length_surveyed} KM` : '-'}</span></div>
                        <div>Incidents Reported: <span className="font-semibold text-slate-800">{survey.ir_count > 0 ? survey.ir_count : '-'}</span></div>
                        <div>Total Defects: <span className="font-semibold text-slate-800">{survey.defects_reported > 0 ? `${survey.defects_reported}` : '-'}</span></div>
                      </div>
                      
                      {/* Column 2: Deliverables & Quality scores */}
                      <div className="text-xs space-y-1 text-slate-500">
                        <div className="font-bold text-slate-800 mb-1.5 uppercase text-[9px] tracking-wider">Quality & Timelines</div>
                        <div className="flex items-center space-x-3.5">
                          <div>Precision Score: <span className={`font-bold ${survey.precision_score >= 0.9 ? 'text-indigo-650' : 'text-slate-800'}`}>{survey.precision_score > 0 ? survey.precision_score.toFixed(3) : '-'}</span></div>
                          <div>Recall Score: <span className={`font-bold ${survey.recall_score >= 0.9 ? 'text-teal-650' : 'text-slate-800'}`}>{survey.recall_score > 0 ? survey.recall_score.toFixed(3) : '-'}</span></div>
                        </div>
                        <div>Report Status: <span className={`font-semibold ${survey.report_submission_status === 'Delayed' ? 'text-rose-600' : 'text-slate-700'}`}>{survey.report_submission_status || '-'}</span></div>
                        <div>
                          Report Delay: <span className="font-semibold text-slate-800">
                            {survey.total_delay > 0 ? `${survey.total_delay} Days` : 'No Delay'}
                          </span>
                          {survey.delay_d1 > 0 && <span className="text-[10px] text-slate-400 ml-1">(D1: {survey.delay_d1}d, D2: {survey.delay_d2}d)</span>}
                        </div>
                        {survey.discrepancy_date && (
                          <div className="text-rose-600 font-medium flex items-center space-x-1">
                            <AlertTriangle className="h-3 w-3" />
                            <span>Discrepancy Raised on {survey.discrepancy_date}</span>
                          </div>
                        )}
                      </div>
                      
                      {/* Column 3: Links */}
                      <div className="text-xs space-y-1.5 text-slate-500 no-print">
                        <div className="font-bold text-slate-800 mb-1 uppercase text-[9px] tracking-wider">Attachments & Links</div>
                        
                        <div className="grid grid-cols-2 gap-1.5 text-[10px] font-semibold">
                          {survey.raw_video_link && (
                            <a href={survey.raw_video_link} target="_blank" rel="noreferrer" className="flex items-center space-x-1 text-slate-700 hover:text-nhai-orange bg-slate-50 hover:bg-slate-100 border border-slate-200/60 p-1.5 rounded transition">
                              <ExternalLink className="h-3 w-3 text-slate-400" />
                              <span className="truncate">Raw Video</span>
                            </a>
                          )}
                          {survey.processed_video_link && (
                            <a href={survey.processed_video_link} target="_blank" rel="noreferrer" className="flex items-center space-x-1 text-slate-700 hover:text-nhai-orange bg-slate-50 hover:bg-slate-100 border border-slate-200/60 p-1.5 rounded transition">
                              <ExternalLink className="h-3 w-3 text-slate-400" />
                              <span className="truncate">Processed Video</span>
                            </a>
                          )}
                          {survey.final_survey_report_link && (
                            <a href={survey.final_survey_report_link} target="_blank" rel="noreferrer" className="flex items-center space-x-1 text-slate-700 hover:text-nhai-orange bg-slate-50 hover:bg-slate-100 border border-slate-200/60 p-1.5 rounded transition">
                              <ExternalLink className="h-3 w-3 text-slate-400" />
                              <span className="truncate">Survey Report</span>
                            </a>
                          )}
                          {survey.assessed_report_link && (
                            <a href={survey.assessed_report_link} target="_blank" rel="noreferrer" className="flex items-center space-x-1 text-slate-700 hover:text-nhai-orange bg-slate-50 hover:bg-slate-100 border border-slate-200/60 p-1.5 rounded transition">
                              <ExternalLink className="h-3 w-3 text-slate-400" />
                              <span className="truncate">Assessed Report</span>
                            </a>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Remarks and Comments if present */}
                    {(survey.remarks || survey.comments) && (
                      <div className="bg-slate-50/70 border border-slate-100 rounded-lg p-2.5 mt-3 text-[11px] text-slate-650">
                        {survey.remarks && <div><span className="font-semibold text-slate-800">Remarks:</span> {survey.remarks}</div>}
                        {survey.comments && <div><span className="font-semibold text-slate-800">Comments:</span> {survey.comments}</div>}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-slate-400 italic text-xs py-4">No detailed survey runs schedule found for this project in selected filters.</p>
          )}
        </div>
      )}
    </div>
  );
};
