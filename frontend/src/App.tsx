import { useState, useEffect } from 'react';
import { 
  useFilters, useDashboard, useZoneDrilldown, useRODrilldown, usePIUDrilldown,
  useProjectDrilldown, useRefreshCache, useConnectionStatus 
} from './hooks/useDashboardData';
import type { DashboardFilters } from './hooks/useDashboardData';
import { Navbar } from './components/Navbar';
import { StickyFilterPanel } from './components/filters/StickyFilterPanel';
import { MetricCards } from './components/cards/MetricCards';
import { ZoneTable } from './components/tables/ZoneTable';
import { DrillDowns } from './components/tables/DrillDowns';
import { DashboardCharts } from './components/charts/DashboardCharts';
import { Settings } from './components/Settings';
import { LayoutDashboard, Loader2, AlertTriangle, Settings as SettingsIcon } from 'lucide-react';

function App() {
  // 1. App Navigation State
  const [showSettings, setShowSettings] = useState(false);

  // 2. Filter States
  const [filters, setFilters] = useState<DashboardFilters>({});
  
  // 3. Progressive Drilldown States
  const [selectedZone, setSelectedZone] = useState<string | null>(null);
  const [selectedRO, setSelectedRO] = useState<string | null>(null);
  const [selectedPIU, setSelectedPIU] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [selectedProjectName, setSelectedProjectName] = useState<string | null>(null);

  // 4. React Query Queries & Mutations
  const { data: connStatus, isLoading: isLoadingStatus } = useConnectionStatus();
  const { data: filterOptions, isLoading: isLoadingOptions } = useFilters();
  
  const dashboardQuery = useDashboard(filters);
  const { data: dashboardData, isLoading: isLoadingDashboard, isFetching: isFetchingDashboard, error: dashboardError, isError: isDashboardError } = dashboardQuery;
  
  const { data: roData, isLoading: isLoadingRO } = useZoneDrilldown(selectedZone, filters);
  const { data: piuData, isLoading: isLoadingPIU } = useRODrilldown(selectedRO, filters);
  const { data: projectData, isLoading: isLoadingProject } = usePIUDrilldown(selectedPIU, selectedRO, filters);
  const { data: surveyData, isLoading: isLoadingSurveys } = useProjectDrilldown(selectedProject, filters);

  const refreshMutation = useRefreshCache();

  // 5. Progressive Loading Text
  const [loadingStep, setLoadingStep] = useState(0);
  const showLoader = isLoadingDashboard || isFetchingDashboard || refreshMutation.isPending;

  useEffect(() => {
    if (showLoader) {
      const timer1 = setTimeout(() => setLoadingStep(1), 1000);
      const timer2 = setTimeout(() => setLoadingStep(2), 2200);
      return () => {
        clearTimeout(timer1);
        clearTimeout(timer2);
      };
    } else {
      setLoadingStep(0);
    }
  }, [showLoader]);

  const getLoadingText = () => {
    if (loadingStep === 0) return "Loading worksheets...";
    if (loadingStep === 1) return "Reading Project Details...";
    return "Processing summaries...";
  };

  // 6. Config checks & error handlers
  const isConfigError = isDashboardError && (dashboardError as any)?.response?.status === 412;
  const detailError = isDashboardError ? ((dashboardError as any)?.response?.data?.detail || (dashboardError as any)?.message) : null;
  const isSheetMissing = connStatus?.status === 'Not Connected' || !connStatus?.spreadsheet_name || isConfigError;

  // Auto-redirect to settings on configuration error
  useEffect(() => {
    if (isConfigError) {
      setShowSettings(true);
    }
  }, [isConfigError]);

  const handleFilterChange = (newFilters: DashboardFilters) => {
    setFilters(newFilters);
    if (newFilters.zone && newFilters.zone !== selectedZone) {
      setSelectedZone(newFilters.zone);
      setSelectedRO(null);
      setSelectedPIU(null);
      setSelectedProject(null);
      setSelectedProjectName(null);
    } else if (!newFilters.zone) {
      setSelectedZone(null);
      setSelectedRO(null);
      setSelectedPIU(null);
      setSelectedProject(null);
      setSelectedProjectName(null);
    }
    
    if (newFilters.ro && newFilters.ro !== selectedRO) {
      setSelectedRO(newFilters.ro);
      setSelectedPIU(null);
      setSelectedProject(null);
      setSelectedProjectName(null);
    }
    
    if (newFilters.piu && newFilters.piu !== selectedPIU) {
      setSelectedPIU(newFilters.piu);
      setSelectedProject(null);
      setSelectedProjectName(null);
    }
  };

  const handleSelectZone = (zone: string | null) => {
    setSelectedZone(zone);
    setSelectedRO(null);
    setSelectedPIU(null);
    setSelectedProject(null);
    setSelectedProjectName(null);
    setFilters(prev => ({
      ...prev,
      zone: zone || undefined,
      ro: undefined
    }));
  };

  const handleSelectRO = (ro: string | null) => {
    setSelectedRO(ro);
    setSelectedPIU(null);
    setSelectedProject(null);
    setSelectedProjectName(null);
    setFilters(prev => ({
      ...prev,
      ro: ro || undefined,
      piu: undefined
    }));
  };

  const handleSelectPIU = (piu: string | null) => {
    setSelectedPIU(piu);
    setSelectedProject(null);
    setSelectedProjectName(null);
    setFilters(prev => ({
      ...prev,
      piu: piu || undefined
    }));
  };

  const handleSelectProject = (upc: string | null, name: string | null) => {
    setSelectedProject(upc);
    setSelectedProjectName(name);
  };

  const handleRefresh = () => {
    refreshMutation.mutate();
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* 1. Navbar */}
      <Navbar 
        connStatus={connStatus}
        isLoadingStatus={isLoadingStatus}
        isRefreshing={refreshMutation.isPending} 
        onOpenSettings={() => setShowSettings(true)}
        showSettingsBtn={!showSettings}
      />

      {/* 2. Settings Panel View */}
      {showSettings ? (
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Settings 
            onBackToDashboard={() => setShowSettings(false)} 
            canGoBack={!isSheetMissing}
          />
        </main>
      ) : (
        /* 3. Main Dashboard View */
        <>
          {/* Sticky Filters */}
          <StickyFilterPanel 
            filters={filters} 
            onChangeFilters={handleFilterChange}
            filterOptions={filterOptions}
            isLoadingOptions={isLoadingOptions}
            onRefresh={handleRefresh}
            isRefreshing={refreshMutation.isPending}
          />

          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
            {/* Hidden Print Header (PDF Export) */}
            <div className="hidden print:block border-b-2 border-slate-800 pb-4 mb-6">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">National Highways Authority of India (NHAI)</h1>
                  <h2 className="text-lg font-bold text-slate-650 mt-1">Executive Road Survey Monitoring Report</h2>
                </div>
                <span className="text-sm font-mono text-slate-500 bg-slate-100 px-3 py-1 rounded-lg">OFFICIAL USE ONLY</span>
              </div>
              
              <div className="grid grid-cols-2 gap-4 mt-4 text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                <div>Generated: {new Date().toLocaleString()}</div>
                <div className="text-right">Active Filters: {Object.keys(filters).length > 0 ? JSON.stringify(filters) : 'All Records'}</div>
              </div>
            </div>

            {/* Error state alert panel */}
            {isDashboardError && (
              <div className="bg-rose-50 border border-rose-200 rounded-xl p-5 shadow-sm text-slate-750 flex items-start space-x-3.5 animate-slide-up no-print">
                <AlertTriangle className="h-6 w-6 text-rose-500 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h4 className="font-bold text-rose-800 text-sm">Dashboard Data Connection Failure</h4>
                  <p className="text-xs text-rose-700">{detailError}</p>
                  <button
                    onClick={() => setShowSettings(true)}
                    className="mt-3 text-xs font-bold text-nhai-blue hover:text-nhai-blue-dark flex items-center space-x-1 border border-slate-200 bg-white px-3 py-1.5 rounded-lg hover:bg-slate-50 transition"
                  >
                    <SettingsIcon className="h-3.5 w-3.5" />
                    <span>Open Settings & Re-Configure</span>
                  </button>
                </div>
              </div>
            )}

            {/* Global Loader Overlay */}
            {showLoader && (
              <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center no-print">
                <div className="bg-white border border-slate-250 p-6 rounded-2xl shadow-xl flex flex-col items-center justify-center space-y-3.5 max-w-sm w-full mx-4">
                  <Loader2 className="h-9 w-9 animate-spin text-nhai-blue" />
                  <div className="text-center">
                    <p className="text-slate-800 font-bold text-sm tracking-tight">{getLoadingText()}</p>
                    <p className="text-slate-400 text-[10px] mt-0.5">Please wait, compiling spreadsheet rows...</p>
                  </div>
                </div>
              </div>
            )}

            {/* 4. Executive KPI Summary Cards */}
            {!isDashboardError && (
              <div className="print-card">
                <MetricCards 
                  kpis={dashboardData?.kpis} 
                  isLoading={isLoadingDashboard} 
                />
              </div>
            )}

            {/* 5. Main Dashboard Grid (Tables and Drilldowns) */}
            {!isDashboardError && (
              <div className="grid grid-cols-1 gap-6">
                {/* Main Zone Aggregation table */}
                <div className="print-card">
                  <ZoneTable 
                    data={dashboardData?.zone_table}
                    isLoading={isLoadingDashboard}
                    selectedZone={selectedZone}
                    onSelectZone={handleSelectZone}
                  />
                </div>

                {/* Drill-down sections (RO -> PIUs -> Projects -> Surveys) */}
                <DrillDowns 
                  selectedZone={selectedZone}
                  selectedRO={selectedRO}
                  selectedPIU={selectedPIU}
                  selectedProject={selectedProject}
                  selectedProjectName={selectedProjectName}
                  onSelectZone={handleSelectZone}
                  onSelectRO={handleSelectRO}
                  onSelectPIU={handleSelectPIU}
                  onSelectProject={handleSelectProject}
                  roData={roData}
                  piuData={piuData}
                  projectData={projectData}
                  surveyData={surveyData}
                  isLoadingRO={isLoadingRO}
                  isLoadingPIU={isLoadingPIU}
                  isLoadingProject={isLoadingProject}
                  isLoadingSurveys={isLoadingSurveys}
                />
              </div>
            )}

            {/* 6. Dashboard Analytics Charts */}
            {!isDashboardError && (
              <div className="print-page-break print-card">
                <div className="flex items-center space-x-2 pb-2 mb-1 border-b border-slate-200 no-print">
                  <LayoutDashboard className="h-5 w-5 text-nhai-blue" />
                  <h3 className="font-bold text-slate-800 text-sm">Visual Performance Analytics</h3>
                </div>
                
                <DashboardCharts 
                  data={dashboardData?.charts}
                  isLoading={isLoadingDashboard}
                />
              </div>
            )}
          </main>
        </>
      )}

      {/* 7. Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 mt-12 no-print">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-[10px] font-bold text-slate-400 uppercase tracking-wider">
          © {new Date().getFullYear()} National Highways Authority of India. All rights reserved.
        </div>
      </footer>
    </div>
  );
}

export default App;
