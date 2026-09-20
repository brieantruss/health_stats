import React, { useState } from 'react';
import {
  HeartPulse,
  Moon,
  Footprints,
  Navigation,
  Flame,
  Bike,
  Waves,
  CircleDot,
  Activity,
  Wind,
  Gauge,
  MapPin,
  CloudSun,
  FileText,
  Clock,
  HardDrive,
  Check,
  Copy,
  AlertCircle,
} from 'lucide-react';
import { CategoryTelemetry } from '../types/pipeline';
import { CATEGORY_CONFIG, formatRelativeTime, formatExactDateTime } from '../utils/formatters';

interface CategoryCardProps {
  telemetry: CategoryTelemetry;
}

// Icon mapper for dynamic category icons
const renderCategoryIcon = (iconName: string, className: string) => {
  switch (iconName) {
    case 'HeartPulse': return <HeartPulse className={className} />;
    case 'Moon': return <Moon className={className} />;
    case 'Footprints': return <Footprints className={className} />;
    case 'Navigation': return <Navigation className={className} />;
    case 'Flame': return <Flame className={className} />;
    case 'Bike': return <Bike className={className} />;
    case 'Waves': return <Waves className={className} />;
    case 'CircleDot': return <CircleDot className={className} />;
    case 'Activity': return <Activity className={className} />;
    case 'Wind': return <Wind className={className} />;
    case 'Gauge': return <Gauge className={className} />;
    case 'MapPin': return <MapPin className={className} />;
    case 'CloudSun': return <CloudSun className={className} />;
    default: return <Activity className={className} />;
  }
};

export const CategoryCard: React.FC<CategoryCardProps> = ({ telemetry }) => {
  const [copied, setCopied] = useState(false);
  const config = CATEGORY_CONFIG[telemetry.category] || {
    label: telemetry.category,
    iconName: 'Activity',
    color: 'text-slate-400',
    accentBg: 'bg-slate-500/10',
    borderColor: 'border-slate-500/30',
    description: '',
  };

  const handleCopyFileName = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (telemetry.latestFileName) {
      navigator.clipboard.writeText(telemetry.latestFileName);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const hasFiles = telemetry.totalFiles > 0;

  return (
    <div
      className={`relative rounded-xl bg-slate-900/90 border transition-all duration-300 p-4 flex flex-col justify-between overflow-hidden group ${
        telemetry.isPulsing
          ? 'border-cyan-400 ring-2 ring-cyan-400/30 shadow-lg shadow-cyan-500/10'
          : hasFiles
          ? 'border-slate-800 hover:border-slate-700/80 hover:bg-slate-850/80'
          : 'border-slate-800/60 opacity-60 hover:opacity-100 hover:border-slate-700'
      }`}
    >
      {/* Visual pulse glow on update */}
      {telemetry.isPulsing && (
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-transparent animate-pulse pointer-events-none" />
      )}

      {/* Top Header */}
      <div>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2.5">
            <div className={`p-2.5 rounded-xl ${config.accentBg} ${config.color} border ${config.borderColor}`}>
              {renderCategoryIcon(config.iconName, 'w-5 h-5')}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-1.5">
                {config.label}
                {telemetry.isPulsing && (
                  <span className="inline-flex h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
                )}
              </h3>
              <p className="text-[11px] text-slate-400 line-clamp-1">{config.description}</p>
            </div>
          </div>

          <div className="flex flex-col items-end gap-1">
            <span
              className={`px-2 py-0.5 rounded-full text-[11px] font-semibold tracking-wide border ${
                hasFiles
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-slate-800 text-slate-400 border-slate-700/50'
              }`}
            >
              {telemetry.totalFiles} {telemetry.totalFiles === 1 ? 'file' : 'files'}
            </span>
            {telemetry.pendingRawFiles > 0 && (
              <span className="text-[10px] text-amber-400/90 font-mono flex items-center gap-0.5">
                <AlertCircle className="w-2.5 h-2.5" /> {telemetry.pendingRawFiles} in raw/
              </span>
            )}
          </div>
        </div>

        {/* Storage Volume pill */}
        {hasFiles && (
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-3 px-2 py-1 rounded bg-slate-950/60 border border-slate-800/60 w-fit">
            <HardDrive className="w-3 h-3 text-slate-500" />
            <span>{telemetry.totalSizeFormatted}</span>
          </div>
        )}
      </div>

      {/* Latest File & Timestamp Section */}
      <div className="pt-3 border-t border-slate-800/80 mt-2 space-y-2">
        <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
          <span className="flex items-center gap-1 text-slate-400">
            <FileText className="w-3.5 h-3.5 text-slate-500" />
            Latest Ingested File:
          </span>
          {telemetry.latestFileSizeFormatted && (
            <span className="text-slate-500 font-mono text-[10px]">
              {telemetry.latestFileSizeFormatted}
            </span>
          )}
        </div>

        {telemetry.latestFileName ? (
          <div className="flex items-center justify-between gap-2 p-2 rounded-lg bg-slate-950/80 border border-slate-800/70 hover:border-slate-700/80 group/file transition-colors">
            <div
              className="font-mono text-xs text-slate-200 truncate flex-1"
              title={telemetry.latestFileName}
            >
              {telemetry.latestFileName}
            </div>
            <button
              onClick={handleCopyFileName}
              title="Copy filename"
              className="text-slate-500 hover:text-slate-200 p-1 rounded hover:bg-slate-800 transition-colors"
            >
              {copied ? (
                <Check className="w-3 h-3 text-emerald-400" />
              ) : (
                <Copy className="w-3 h-3 opacity-0 group-hover/file:opacity-100 transition-opacity" />
              )}
            </button>
          </div>
        ) : (
          <div className="text-xs text-slate-500 italic py-1">No files ingested yet</div>
        )}

        {/* Timestamp */}
        <div className="flex items-center justify-between text-[11px] pt-1">
          <span className="text-slate-500 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Timestamp:
          </span>
          <span
            className="text-slate-300 font-medium cursor-help hover:text-cyan-400 transition-colors"
            title={formatExactDateTime(telemetry.latestFileModifiedAt)}
          >
            {formatRelativeTime(telemetry.latestFileModifiedAt)}
          </span>
        </div>
      </div>
    </div>
  );
};
