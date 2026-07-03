import React, { useState, useMemo } from 'react';
import { getExportUrl } from '../../hooks/useDashboardData';
import type { FilterOptions, DashboardFilters, WeekOption } from '../../hooks/useDashboardData';
import { Search, RotateCw, Download, Printer, Filter, X, FileSpreadsheet, FileText, Calendar, MapPin, ChevronDown } from 'lucide-react';

interface StickyFilterPanelProps {
  filters: DashboardFilters;
  onChangeFilters: (newFilters: DashboardFilters) => void;
  filterOptions: FilterOptions | undefined;
  isLoadingOptions: boolean;
  onRefresh: () => void;
  isRefreshing: boolean;
}

const FilterSelect: React.FC<{
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  placeholder: string;
  children: React.ReactNode;
  icon?: React.ReactNode;
}> = ({ value, onChange, disabled, placeholder, children, icon }) => (
  <div className="relative">
    {icon && (
      <div className="pointer-events-none absolute inset-y-0 left-2.5 flex items-center text-slate-400 z-10">
        {icon}
      </div>
    )}
    <select
      className={`w-full appearance-none bg-slate-50 border border-slate-200 text-slate-700 py-2 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors cursor-pointer ${icon ? 'pl-7 pr-7' : 'pl-2.5 pr-7'} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      value={value}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
    >
      <option value="">{placeholder}</option>
      {children}
    </select>
    <ChevronDown className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-400" />
  </div>
);

export const StickyFilterPanel: React.FC<StickyFilterPanelProps> = ({
  filters,
  onChangeFilters,
  filterOptions,
  isLoadingOptions,
  onRefresh,
  isRefreshing,
}) => {
  const [showExports, setShowExports] = useState(false);
  const [tempSearch, setTempSearch] = useState(filters.search || '');

  // Cascaded months based on selected year
  const filteredMonths = useMemo(() => {
    if (!filterOptions?.weeks || !filters.year) return filterOptions?.months ?? [];
    const monthsForYear = new Set(
      filterOptions.weeks
        .filter(w => w.year === filters.year)
        .map(w => w.month)
    );
    const order = ["January","February","March","April","May","June","July","August","September","October","November","December"];
    return order.filter(m => monthsForYear.has(m));
  }, [filterOptions, filters.year]);

  // Cascaded weeks based on selected year + month
  const filteredWeeks = useMemo((): WeekOption[] => {
    if (!filterOptions?.weeks) return [];
    return filterOptions.weeks.filter(w => {
      if (filters.year && w.year !== filters.year) return false;
      if (filters.month && w.month !== filters.month) return false;
      return true;
    });
  }, [filterOptions, filters.year, filters.month]);

  const handleChange = (key: keyof DashboardFilters, value: string | number | undefined) => {
    const updated: DashboardFilters = { ...filters, [key]: value || undefined };
    // Cascade resets on parent change
    if (key === 'year') { updated.month = undefined; updated.week_label = undefined; }
    if (key === 'month') { updated.week_label = undefined; }
    if (key === 'zone') { updated.ro = undefined; updated.piu = undefined; }
    if (key === 'ro') { updated.piu = undefined; }
    onChangeFilters(updated);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onChangeFilters({ ...filters, search: tempSearch.trim() || undefined });
  };

  const handleClearAll = () => {
    setTempSearch('');
    onChangeFilters({});
  };

  const hasActiveFilters = Object.values(filters).some(v => v !== undefined);

  const filterLabels: Partial<Record<keyof DashboardFilters, string>> = {
    year: 'Year', month: 'Month', week_label: 'Week',
    zone: 'Zone', ro: 'RO', piu: 'PIU', status: 'Status', search: 'Search'
  };

  return (
    <div className="sticky top-16 z-40 bg-white/97 backdrop-blur-md border-b border-slate-200 shadow-sm py-3 no-print transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <form onSubmit={handleSearchSubmit} className="space-y-2">

          {/* Row 1: Date Hierarchy + Location + Search */}
          <div className="flex flex-wrap gap-2 items-end">

            {/* Date group label */}
            <div className="flex items-center text-xs text-slate-500 font-semibold gap-1 mr-1 shrink-0 self-center">
              <Calendar className="h-3.5 w-3.5 text-blue-500" />
              <span>Date:</span>
            </div>

            {/* Year */}
            <div className="w-24">
              <FilterSelect
                value={String(filters.year ?? '')}
                onChange={v => handleChange('year', v ? parseInt(v) : undefined)}
                disabled={isLoadingOptions}
                placeholder="All Years"
              >
                {filterOptions?.years.map(y => <option key={y} value={y}>{y}</option>)}
              </FilterSelect>
            </div>

            {/* Month */}
            <div className="w-28">
              <FilterSelect
                value={filters.month ?? ''}
                onChange={v => handleChange('month', v)}
                disabled={isLoadingOptions || !filterOptions}
                placeholder="All Months"
              >
                {filteredMonths.map(m => <option key={m} value={m}>{m}</option>)}
              </FilterSelect>
            </div>

            {/* Week */}
            <div className="w-56">
              <FilterSelect
                value={filters.week_label ?? ''}
                onChange={v => handleChange('week_label', v)}
                disabled={isLoadingOptions || !filterOptions}
                placeholder="All Weeks"
              >
                {filteredWeeks.map(w => <option key={w.label} value={w.label}>{w.label}</option>)}
              </FilterSelect>
            </div>

            <div className="h-4 w-px bg-slate-200 mx-1 self-center hidden sm:block" />

            {/* Location group label */}
            <div className="flex items-center text-xs text-slate-500 font-semibold gap-1 shrink-0 self-center">
              <MapPin className="h-3.5 w-3.5 text-orange-500" />
              <span>Location:</span>
            </div>

            {/* Zone */}
            <div className="w-28">
              <FilterSelect
                value={filters.zone ?? ''}
                onChange={v => handleChange('zone', v)}
                disabled={isLoadingOptions}
                placeholder="All Zones"
              >
                {filterOptions?.zones.map(z => <option key={z} value={z}>{z} Zone</option>)}
              </FilterSelect>
            </div>

            {/* RO */}
            <div className="w-36">
              <FilterSelect
                value={filters.ro ?? ''}
                onChange={v => handleChange('ro', v)}
                disabled={isLoadingOptions}
                placeholder="All ROs"
              >
                {filterOptions?.ros.map(r => <option key={r} value={r}>{r}</option>)}
              </FilterSelect>
            </div>

            {/* PIU */}
            <div className="w-36">
              <FilterSelect
                value={filters.piu ?? ''}
                onChange={v => handleChange('piu', v)}
                disabled={isLoadingOptions}
                placeholder="All PIUs"
              >
                {filterOptions?.pius.map(p => <option key={p} value={p}>{p}</option>)}
              </FilterSelect>
            </div>

            {/* Search */}
            <div className="flex-1 min-w-[180px] relative">
              <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-400">
                <Search className="h-3.5 w-3.5" />
              </div>
              <input
                type="text"
                placeholder="Search Project, UPC, RO, PIU…"
                className="w-full pl-8 pr-7 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-slate-700 transition"
                value={tempSearch}
                onChange={e => setTempSearch(e.target.value)}
              />
              {tempSearch && (
                <button type="button"
                  onClick={() => { setTempSearch(''); onChangeFilters({ ...filters, search: undefined }); }}
                  className="absolute inset-y-0 right-0 pr-2 flex items-center text-slate-400 hover:text-slate-600">
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <button type="submit" className="hidden">Search</button>
          </div>

          {/* Row 2: Active filter chips + Action buttons */}
          <div className="flex items-center justify-between pt-1 border-t border-slate-100">
            <div className="flex items-center gap-2 text-xs flex-wrap">
              <span className="text-slate-400 flex items-center gap-1">
                <Filter className="h-3.5 w-3.5" />
                <span>Active:</span>
              </span>
              {hasActiveFilters ? (
                <>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(filters).map(([key, val]) => {
                      if (!val) return null;
                      const label = filterLabels[key as keyof DashboardFilters] ?? key;
                      return (
                        <span key={key}
                          className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full text-[10px] font-medium">
                          <span className="opacity-60">{label}:</span>
                          <span>{String(val)}</span>
                          <button type="button"
                            onClick={() => handleChange(key as keyof DashboardFilters, undefined)}
                            className="hover:text-red-500 ml-0.5">&times;</button>
                        </span>
                      );
                    })}
                  </div>
                  <button type="button" onClick={handleClearAll}
                    className="text-slate-500 hover:text-red-500 underline text-[10px] font-semibold">
                    Clear All
                  </button>
                </>
              ) : (
                <span className="text-slate-400 italic text-[11px]">None active — showing all surveys</span>
              )}
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button type="button" onClick={onRefresh}
                className={`flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${isRefreshing ? 'opacity-70 pointer-events-none' : ''}`}
                title="Reload data from Google Sheets">
                <RotateCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>

              <button type="button" onClick={() => window.print()}
                className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold transition">
                <Printer className="h-3.5 w-3.5" />
                <span>Print</span>
              </button>

              <div className="relative">
                <button type="button" onClick={() => setShowExports(!showExports)}
                  className="flex items-center gap-1.5 bg-orange-500 hover:bg-orange-600 text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition shadow-sm">
                  <Download className="h-3.5 w-3.5" />
                  <span>Export</span>
                </button>
                {showExports && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setShowExports(false)} />
                    <div className="absolute right-0 mt-1.5 w-36 bg-white border border-slate-200 rounded-lg shadow-lg py-1.5 z-20 text-xs">
                      <a href={getExportUrl('csv', filters)}
                        className="flex items-center gap-2 px-3.5 py-2 text-slate-700 hover:bg-slate-50 transition"
                        onClick={() => setShowExports(false)}>
                        <FileText className="h-3.5 w-3.5 text-blue-500" />
                        <span>Export as CSV</span>
                      </a>
                      <a href={getExportUrl('excel', filters)}
                        className="flex items-center gap-2 px-3.5 py-2 text-slate-700 hover:bg-slate-50 transition"
                        onClick={() => setShowExports(false)}>
                        <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600" />
                        <span>Export as Excel</span>
                      </a>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

        </form>
      </div>
    </div>
  );
};
