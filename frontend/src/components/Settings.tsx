import React, { useState, useEffect } from 'react';
import { 
  useSettings, useSaveSettings, useTestConnection
} from '../hooks/useDashboardData';
import type { ConnectionTestResult } from '../hooks/useDashboardData';
import { 
  Settings as SettingsIcon, Save, Activity, ArrowLeft, Loader2, 
  CheckCircle2, XCircle, AlertTriangle, FileSpreadsheet, Key, Clock
} from 'lucide-react';

interface SettingsProps {
  onBackToDashboard: () => void;
  canGoBack: boolean;
}

export const Settings: React.FC<SettingsProps> = ({ onBackToDashboard, canGoBack }) => {
  const { data: initialSettings, isLoading: isLoadingInitial } = useSettings();
  const saveSettingsMutation = useSaveSettings();
  const testConnectionMutation = useTestConnection();

  const [sheetUrl, setSheetUrl] = useState('');
  const [credsFile, setCredsFile] = useState('credentials.json');
  const [apiKey, setApiKey] = useState('');
  const [cacheExpiry, setCacheExpiry] = useState(300);

  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Initialize values when settings load
  useEffect(() => {
    if (initialSettings) {
      setSheetUrl(initialSettings.google_sheet_url || '');
      setCredsFile(initialSettings.google_credentials_file || 'credentials.json');
      setApiKey(initialSettings.google_api_key || '');
      setCacheExpiry(initialSettings.cache_expiry_seconds || 300);
    }
  }, [initialSettings]);

  const handleTestConnection = () => {
    setTestResult(null);
    setTestError(null);
    
    testConnectionMutation.mutate({
      google_sheet_url: sheetUrl,
      google_credentials_file: credsFile,
      google_api_key: apiKey || undefined
    }, {
      onSuccess: (data) => {
        setTestResult(data);
      },
      onError: (err: any) => {
        setTestError(err.response?.data?.detail || err.message || 'Connection failed.');
      }
    });
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(false);
    setSaveError(null);
    
    saveSettingsMutation.mutate({
      google_sheet_url: sheetUrl,
      google_credentials_file: credsFile,
      google_api_key: apiKey || undefined,
      cache_expiry_seconds: Number(cacheExpiry)
    }, {
      onSuccess: () => {
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 4000);
      },
      onError: (err: any) => {
        setSaveError(err.response?.data?.detail || err.message || 'Failed to save configuration.');
      }
    });
  };

  if (isLoadingInitial) {
    return (
      <div className="max-w-3xl mx-auto my-12 bg-white border border-slate-200 rounded-xl p-8 shadow-sm flex flex-col items-center justify-center h-64">
        <Loader2 className="h-8 w-8 text-nhai-blue animate-spin mb-3" />
        <p className="text-slate-500 text-sm font-semibold">Loading Configuration Settings...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto my-6 animate-slide-up">
      {/* Header card */}
      <div className="flex items-center justify-between mb-4 bg-white border border-slate-250/80 px-5 py-4 rounded-xl shadow-sm">
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-nhai-blue/5 rounded-lg border border-nhai-blue/10">
            <SettingsIcon className="h-5 w-5 text-nhai-blue" />
          </div>
          <div>
            <h2 className="font-bold text-slate-800 text-sm">Dashboard Configuration Settings</h2>
            <p className="text-slate-400 text-[11px] mt-0.5 font-medium">Link Google Spreadsheet and manage data refresh intervals</p>
          </div>
        </div>
        
        {canGoBack && (
          <button
            onClick={onBackToDashboard}
            className="flex items-center space-x-1 text-xs font-bold text-slate-650 hover:text-nhai-blue border border-slate-200 px-3 py-1.5 rounded-lg hover:bg-slate-50 transition"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Dashboard</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6">
        {/* Form panel */}
        <form onSubmit={handleSave} className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden p-6 space-y-4">
          <h3 className="text-xs uppercase font-bold tracking-wider text-slate-400 border-b border-slate-100 pb-2 mb-2">
            Google Sheets API Connectivity
          </h3>

          {/* Alert if not configured */}
          {!canGoBack && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 flex items-start space-x-2">
              <AlertTriangle className="h-4.5 w-4.5 text-amber-500 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">No Google Spreadsheet configured.</span> Please enter your Spreadsheet URL and credentials setup below to initialize the dashboard summaries.
              </div>
            </div>
          )}

          {/* URL Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 block">
              Google Spreadsheet URL <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. https://docs.google.com/spreadsheets/d/your-spreadsheet-id/edit"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-nhai-blue font-medium"
              value={sheetUrl}
              onChange={(e) => setSheetUrl(e.target.value)}
            />
            <p className="text-[10px] text-slate-400 font-medium">
              Copy-paste the full URL of the spreadsheet. Ensure it contains the "Project Details" worksheet and RO worksheets.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Credentials JSON */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 flex items-center space-x-1.5">
                <FileSpreadsheet className="h-3.5 w-3.5 text-slate-400" />
                <span>Service Account Credentials Path</span>
              </label>
              <input
                type="text"
                placeholder="e.g. credentials.json"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-nhai-blue font-mono"
                value={credsFile}
                onChange={(e) => setCredsFile(e.target.value)}
              />
              <p className="text-[10px] text-slate-400 font-medium">
                JSON credentials filename or path in backend root directory.
              </p>
            </div>

            {/* API Key */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 flex items-center space-x-1.5">
                <Key className="h-3.5 w-3.5 text-slate-400" />
                <span>Google API Key (Public Sheets only)</span>
              </label>
              <input
                type="password"
                placeholder="Optional API Key"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-nhai-blue font-mono"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <p className="text-[10px] text-slate-400 font-medium">
                Used if sheet is publicly viewable but credentials file is not set.
              </p>
            </div>
          </div>

          {/* Cache expiry */}
          <div className="space-y-1.5 max-w-xs">
            <label className="text-xs font-bold text-slate-700 flex items-center space-x-1.5">
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              <span>Cache Expiration Duration (Seconds)</span>
            </label>
            <input
              type="number"
              min="10"
              required
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-nhai-blue font-medium"
              value={cacheExpiry}
              onChange={(e) => setCacheExpiry(Number(e.target.value))}
            />
            <p className="text-[10px] text-slate-400 font-medium">
              Time interval in seconds before re-accessing Google Sheets API. Default: 300 (5 minutes).
            </p>
          </div>

          {/* Test results, Errors and Save Success banners */}
          <div className="space-y-2.5 pt-2">
            {testResult && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3.5 text-xs text-slate-750 flex items-start space-x-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-bold text-emerald-800">Connection Successful!</p>
                  <p>Spreadsheet: <span className="font-semibold">{testResult.spreadsheet_name}</span></p>
                  <p>Worksheets Discovered: <span className="font-semibold font-mono">{testResult.worksheets_count} sheets</span> ({testResult.sheet_names.slice(0, 4).join(', ')}...)</p>
                </div>
              </div>
            )}

            {testError && (
              <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-xs text-rose-800 flex items-start space-x-2">
                <XCircle className="h-5 w-5 text-rose-500 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold">Test Connection Failed:</span> {testError}
                </div>
              </div>
            )}

            {saveSuccess && (
              <div className="bg-emerald-50 border border-emerald-250 rounded-lg p-3 text-xs text-emerald-800 flex items-center space-x-2">
                <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500" />
                <span>Configuration saved successfully! In-memory data updated.</span>
              </div>
            )}

            {saveError && (
              <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-xs text-rose-800 flex items-start space-x-2">
                <XCircle className="h-4.5 w-4.5 text-rose-500 shrink-0" />
                <div>
                  <span className="font-bold">Failed to Save Configuration:</span> {saveError}
                </div>
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-between border-t border-slate-100 pt-4 mt-2">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testConnectionMutation.isPending || saveSettingsMutation.isPending}
              className="flex items-center space-x-1.5 text-xs font-semibold text-slate-700 border border-slate-200 px-4 py-2 rounded-lg bg-slate-50 hover:bg-slate-100 disabled:opacity-60 transition"
            >
              {testConnectionMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Activity className="h-3.5 w-3.5" />
              )}
              <span>Test Connection</span>
            </button>

            <button
              type="submit"
              disabled={saveSettingsMutation.isPending || testConnectionMutation.isPending}
              className="flex items-center space-x-1.5 text-xs font-semibold text-white bg-nhai-blue hover:bg-nhai-blue-dark px-4 py-2 rounded-lg disabled:opacity-60 transition shadow"
            >
              {saveSettingsMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-nhai-orange" />
              ) : (
                <Save className="h-3.5 w-3.5 text-nhai-orange" />
              )}
              <span>Save Configuration</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
