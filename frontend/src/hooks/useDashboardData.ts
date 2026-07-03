import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

// Dynamically determine backend URL: 
// In dev, Vite is on port 5173/5174, so connect to FastAPI on port 8000.
// In production, when compiled and served from FastAPI, use relative path.
const API_URL = import.meta.env.VITE_API_URL || 
  (window.location.port ? `${window.location.protocol}//${window.location.hostname}:8000` : '');

export const api = axios.create({
  baseURL: API_URL,
});

export interface WeekOption {
  label: string;
  start: string;
  end: string;
  year: number;
  month: string;
}

export interface FilterOptions {
  years: number[];
  months: string[];
  weeks: WeekOption[];
  zones: string[];
  ros: string[];
  pius: string[];
  statuses: string[];
}

export interface KPIMetrics {
  // Section 1: Survey Monitoring
  total_surveys_scheduled: number;
  completed: number;
  pending: number;
  scheduled: number;
  cancelled: number;
  completion_rate: number;
  // Section 2: Report Submission
  completed_surveys: number;
  reports_expected: number;
  reports_received: number;
  reports_on_time: number;
  reports_delayed: number;
  // Section 3: Defects
  defects_total: number | null;
  defects_repeated: number | null;
  defects_new: number | null;
  // Section 4: Quality
  average_precision: number | null;
  average_recall: number | null;
  // Section 5: Validation
  reports_validated: number | null;
  reports_pending_validation: number | null;
  piu_communication_completed: number | null;
  piu_communication_pending: number | null;
  // Section 6: Discrepancies
  discrepancies_raised: number | null;
  discrepancies_resolved: number | null;
  discrepancies_pending: number | null;
  // Legacy
  total_scheduled: number;
  on_time_reports: number;
  delayed_reports: number;
  pending_reports: number;
  average_delay: number;
  maximum_delay: number;
  total_surveyed_length: number;
}

export interface ZoneTableRow {
  zone: string;
  scheduled: number;
  completed: number;
  pending: number;
  completion_rate: number;
  reports_received: number;
  on_time: number;
  delayed: number;
  reports_validated: number | null;
  pending_validation: number | null;
  discrepancies: number | null;
  resolved: number | null;
  pending_discrepancies: number | null;
  average_delay: number;
}

export interface ROTableRow {
  ro_name: string;
  zone: string;
  scheduled: number;
  completed: number;
  pending: number;
  completion_rate: number;
  reports_received: number;
  on_time: number;
  delayed: number;
  reports_validated: number | null;
  pending_validation: number | null;
  discrepancies: number | null;
  resolved: number | null;
  pending_discrepancies: number | null;
  average_delay: number;
}

export interface PIUTableRow {
  piu_name: string;
  ro_name: string;
  zone: string;
  scheduled: number;
  completed: number;
  pending: number;
  completion_rate: number;
  reports_received: number;
  on_time: number;
  delayed: number;
  reports_validated: number | null;
  pending_validation: number | null;
  discrepancies: number | null;
  resolved: number | null;
  pending_discrepancies: number | null;
  average_delay: number;
}

export interface ProjectTableRow {
  upc_code: string;
  project_name: string;
  ro_name: string;
  piu_name: string;
  scheduled: number;
  completed: number;
  pending: number;
  completion_rate: number;
  reports_received: number;
  on_time: number;
  delayed: number;
  reports_validated: number | null;
  pending_validation: number | null;
  discrepancies: number | null;
  resolved: number | null;
  pending_discrepancies: number | null;
  average_delay: number;
  precision: number | null;
  recall: number | null;
}

export interface SurveyRecordDetail {
  zone: string;
  ro_name: string;
  piu_name: string;
  project_name: string;
  upc_code: string;
  survey_id: string;
  scheduled_survey_date: string;
  actual_survey_date: string;
  survey_status: string;
  remarks: string;
  raw_data_submission_date: string;
  mcw_length_surveyed: number;
  sr_length_surveyed: number;
  ir_count: number;
  comments: string;
  report_submission_scheduled_date: string;
  report_submission_actual_date: string;
  delay_d1: number;
  report_submission_status: string;
  discrepancy_date: string;
  final_report_submission_scheduled_date: string;
  final_report_submission_actual_date: string;
  final_report_submission_status: string;
  delay_d2: number;
  total_delay: number;
  defects_reported: number;
  repeated_defects: number;
  precision_score: number;
  recall_score: number;
  interim_acceptance_date: string;
  validation_date: string;
  survey_form_link: string;
  raw_video_link: string;
  processed_video_link: string;
  final_survey_report_link: string;
  assessed_report_link: string;
  piu_report_link: string;
}

export interface ChartData {
  completion_pie: { name: string; value: number; color: string }[];
  zone_comparison: { zone: string; scheduled: number; completed: number }[];
  weekly_trend: { monday: string; week_label: string; scheduled: number; completed: number; completion_rate: number }[];
  delay_distribution: { range: string; count: number }[];
  provider_performance: { provider: string; scheduled: number; completed: number; completion_rate: number; precision: number; recall: number }[];
}

export interface DashboardResponse {
  kpis: KPIMetrics;
  zone_table: ZoneTableRow[];
  charts: ChartData;
}

export interface DashboardFilters {
  year?: number;
  month?: string;
  week_label?: string;
  zone?: string;
  ro?: string;
  piu?: string;
  status?: string;
  search?: string;
}

// Helper to sanitize query params
const getParams = (filters: DashboardFilters) => {
  const params: Record<string, string> = {};
  if (filters.year) params.year = String(filters.year);
  if (filters.month) params.month = filters.month;
  if (filters.week_label) params.week_label = filters.week_label;
  if (filters.zone) params.zone = filters.zone;
  if (filters.ro) params.ro = filters.ro;
  if (filters.piu) params.piu = filters.piu;
  if (filters.status) params.status = filters.status;
  if (filters.search) params.search = filters.search;
  return params;
};

// 1. Fetch filters query
export const useFilters = () => {
  return useQuery<FilterOptions>({
    queryKey: ['filters'],
    queryFn: async () => {
      const res = await api.get('/api/filters');
      return res.data;
    },
    staleTime: 1000 * 60 * 10, // 10 minutes cache
  });
};

// 2. Fetch main dashboard query
export const useDashboard = (filters: DashboardFilters) => {
  return useQuery<DashboardResponse>({
    queryKey: ['dashboard', filters],
    queryFn: async () => {
      const res = await api.get('/api/dashboard', { params: getParams(filters) });
      return res.data;
    },
    placeholderData: (prev) => prev,
  });
};

// 3. Drill-down: Zone -> ROs
export const useZoneDrilldown = (zoneName: string | null, filters: DashboardFilters) => {
  return useQuery<ROTableRow[]>({
    queryKey: ['drilldown', 'zone', zoneName, filters],
    queryFn: async () => {
      if (!zoneName) return [];
      const res = await api.get(`/api/drilldown/zone/${encodeURIComponent(zoneName)}`, {
        params: getParams(filters),
      });
      return res.data;
    },
    enabled: !!zoneName,
  });
};

// 4. Drill-down: RO -> PIUs
export const useRODrilldown = (roName: string | null, filters: DashboardFilters) => {
  return useQuery<PIUTableRow[]>({
    queryKey: ['drilldown', 'ro', roName, filters],
    queryFn: async () => {
      if (!roName) return [];
      const res = await api.get(`/api/drilldown/ro/${encodeURIComponent(roName)}`, {
        params: getParams(filters),
      });
      return res.data;
    },
    enabled: !!roName,
  });
};

// 4.5. Drill-down: PIU -> Projects
export const usePIUDrilldown = (piuName: string | null, roName: string | null, filters: DashboardFilters) => {
  return useQuery<ProjectTableRow[]>({
    queryKey: ['drilldown', 'piu', piuName, roName, filters],
    queryFn: async () => {
      if (!piuName) return [];
      const params = getParams(filters);
      if (roName) params.ro = roName; // Send RO as well just in case
      const res = await api.get(`/api/drilldown/piu/${encodeURIComponent(piuName)}`, {
        params,
      });
      return res.data;
    },
    enabled: !!piuName,
  });
};

// 5. Drill-down: Project -> Survey Records
export const useProjectDrilldown = (upcCode: string | null, filters: DashboardFilters) => {
  return useQuery<SurveyRecordDetail[]>({
    queryKey: ['drilldown', 'project', upcCode, filters],
    queryFn: async () => {
      if (!upcCode) return [];
      // Project details endpoint accepts status and week filters
      const params: Record<string, string> = {};
      if (filters.week_label) params.week_label = filters.week_label;
      if (filters.status) params.status = filters.status;
      
      const res = await api.get(`/api/drilldown/project/${encodeURIComponent(upcCode)}`, { params });
      return res.data;
    },
    enabled: !!upcCode,
  });
};

// 6. Refresh Cache Mutation
export const useRefreshCache = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await api.post('/api/refresh');
      return res.data;
    },
    onSuccess: () => {
      // Invalidate all queries to trigger refetch
      queryClient.invalidateQueries();
    },
  });
};

// Export URLs helper
export const getExportUrl = (format: 'csv' | 'excel', filters: DashboardFilters) => {
  const searchParams = new URLSearchParams(getParams(filters));
  return `${API_URL}/api/export/${format}?${searchParams.toString()}`;
};

// --- Settings and Connection Status ---

export interface AppSettings {
  google_sheet_url: string;
  google_credentials_file: string;
  google_api_key?: string;
  cache_expiry_seconds: number;
}

export interface ConnectionStatus {
  status: string;
  spreadsheet_name: string;
  worksheets_count: number;
  last_sync_time: string;
  error_message: string;
}

export interface ConnectionTestResult {
  status: string;
  spreadsheet_name: string;
  worksheets_count: number;
  sheet_names: string[];
}

export const useSettings = () => {
  return useQuery<AppSettings>({
    queryKey: ['settings'],
    queryFn: async () => {
      const res = await api.get('/api/settings');
      return res.data;
    },
    staleTime: 0,
  });
};

export const useSaveSettings = () => {
  const queryClient = useQueryClient();
  return useMutation<AppSettings, Error, AppSettings>({
    mutationFn: async (newSettings) => {
      const res = await api.post('/api/settings', newSettings);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });
};

export const useTestConnection = () => {
  return useMutation<ConnectionTestResult, Error, Partial<AppSettings>>({
    mutationFn: async (params) => {
      const res = await api.post('/api/settings/test-connection', params);
      return res.data;
    },
  });
};

export const useConnectionStatus = () => {
  return useQuery<ConnectionStatus>({
    queryKey: ['connection-status'],
    queryFn: async () => {
      const res = await api.get('/health');
      return {
        status: res.data.spreadsheet_connected ? 'Connected' : 'Spreadsheet Not Connected',
        spreadsheet_name: res.data.spreadsheet_name,
        worksheets_count: res.data.worksheets_loaded,
        last_sync_time: res.data.last_sync,
        error_message: res.data.error_message || '',
      };
    },
    refetchInterval: 1000 * 30, // Poll every 30 seconds
  });
};

