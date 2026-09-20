import React from 'react';
import { Files, HardDrive, Layers, Clock } from 'lucide-react';
import { PipelineStatusResponse } from '../types/pipeline';
import { formatRelativeTime, formatExactDateTime, CATEGORY_CONFIG } from '../utils/formatters';

interface MetricsOverviewProps {
  telemetry: PipelineStatusResponse | null;
}

export const MetricsOverview: React.FC<MetricsOverviewProps> = ({ telemetry }) => {
  if (!telemetry) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 rounded-xl bg-slate-900/60 border border-slate-800 animate-pulse p-4" />
        ))}
      </div>
    );
  }

  const activeCategoriesCount = Object.values(telemetry.categories).filter(
    (c) => c.totalFiles > 0
  ).length;

  const latestCatConfig = telemetry.latestIngestion.category
    ? CATEGORY_CONFIG[telemetry.latestIngestion.category]
    : null;

  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* Total Processed Files */}
      <div className="bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-xl p-4 transition-all duration-200">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-medium uppercase tracking-wider">Total Processed</span>
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
            <Files className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-white tracking-tight">
            {telemetry.grandTotalFiles.toLocaleString()}
          </span>
          <span className="text-xs text-slate-400">files</span>
        </div>
        <div className="mt-2 text-[11px] text-slate-500 flex items-center gap-1">
          <span>Across all tracked categories</span>
        </div>
      </div>

      {/* Total Volume */}
      <div className="bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-xl p-4 transition-all duration-200">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-medium uppercase tracking-wider">Storage Volume</span>
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <HardDrive className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-white tracking-tight">
            {telemetry.grandTotalSizeFormatted}
          </span>
        </div>
        <div className="mt-2 text-[11px] text-slate-500">
          Raw & processed CSV datasets
        </div>
      </div>

      {/* Active Data Streams */}
      <div className="bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-xl p-4 transition-all duration-200">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-medium uppercase tracking-wider">Active Categories</span>
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
            <Layers className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-white tracking-tight">
            {activeCategoriesCount}
          </span>
          <span className="text-xs text-slate-400">/ {telemetry.totalCategories} active</span>
        </div>
        <div className="mt-2 flex items-center gap-1.5 text-[11px] text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Health pipeline online</span>
        </div>
      </div>

      {/* Latest Ingestion */}
      <div className="bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-xl p-4 transition-all duration-200">
        <div className="flex items-center justify-between text-slate-400 mb-2">
          <span className="text-xs font-medium uppercase tracking-wider">Latest Activity</span>
          <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
            <Clock className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-lg font-bold text-white truncate max-w-[180px]" title={telemetry.latestIngestion.fileName || ''}>
            {latestCatConfig?.label || 'None'}
          </span>
          <span className="text-xs text-slate-400">
            {formatRelativeTime(telemetry.latestIngestion.timestamp)}
          </span>
        </div>
        <div
          className="mt-2 text-[11px] text-slate-500 truncate"
          title={`${telemetry.latestIngestion.fileName || ''} • ${formatExactDateTime(telemetry.latestIngestion.timestamp)}`}
        >
          {telemetry.latestIngestion.fileName || 'No files ingested yet'}
        </div>
      </div>
    </section>
  );
};
