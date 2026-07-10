import React from 'react';
import { Loader2, Settings } from 'lucide-react';
import type { ConnectionStatus } from '../hooks/useDashboardData';

interface NavbarProps {
  connStatus: ConnectionStatus | undefined;
  isLoadingStatus: boolean;
  isRefreshing: boolean;
  onOpenSettings: () => void;
  showSettingsBtn: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ 
  connStatus, 
  isLoadingStatus, 
  isRefreshing, 
  onOpenSettings,
  showSettingsBtn
}) => {
  const isConnected = connStatus?.status === 'Connected';

  return (
    <header className="sticky top-0 z-50 bg-[#0A2540] text-white border-b border-slate-800 shadow-md no-print">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">

    <img
        src="/nhai-logo.png"
        alt="NHAI Logo"
        className="h-12 w-auto object-contain"
    />

    <div>
        <div className="flex items-center space-x-2">
            <span className="font-bold text-lg tracking-wider">
                NHAI
            </span>

            <span className="text-xs bg-slate-700 px-2 py-1 rounded">
                OFFICIAL
            </span>
        </div>

        <p className="text-sm text-slate-300">
            DashCam Survey Monitoring Dashboard
        </p>
    </div>

</div>

          {/* Connection Status & Details */}
          <div className="flex items-center space-x-4">
            {/* Status indicator */}
            {isLoadingStatus ? (
              <div className="hidden md:flex items-center space-x-2 bg-slate-800/40 px-3 py-1.5 rounded-full border border-slate-700/60 text-xs text-slate-400">
                <Loader2 className="h-3 w-3 animate-spin text-slate-500" />
                <span>Checking connection status...</span>
              </div>
            ) : connStatus ? (
              <div className="hidden md:flex items-center space-x-2 bg-slate-800/60 px-3.5 py-1.5 rounded-full border border-slate-700 text-xs shadow-inner">
                <span className={`h-2 w-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500 animate-pulse'}`} />
                <span className="text-slate-200 font-medium">
                  {isConnected ? (
                    <span>
                      Database <span className="font-bold text-emerald-400">Connected</span> ({connStatus.worksheets_count} surveys loaded)
                    </span>
                  ) : (
                    <span>Database Not Connected</span>
                  )}
                </span>
              </div>
            ) : null}

            {/* Last Synced Time */}
            {connStatus?.last_sync_time && (
              <div className="hidden lg:flex items-center space-x-1.5 text-xs text-slate-400">
                {isRefreshing && <Loader2 className="h-3.5 w-3.5 animate-spin text-nhai-orange mr-0.5" />}
                <span className="font-semibold text-slate-300">Last Synced:</span>
                <span className="font-mono">{connStatus.last_sync_time.split(' ')[1] || connStatus.last_sync_time}</span>
              </div>
            )}

            {/* Settings button */}
            {showSettingsBtn && (
              <button
                onClick={onOpenSettings}
                className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition flex items-center justify-center"
                title="Configure Google Spreadsheet Settings"
              >
                <Settings className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
