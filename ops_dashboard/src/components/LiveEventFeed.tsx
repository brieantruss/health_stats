import React, { useState } from 'react';
import {
  Radio,
  Trash2,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  FileCheck,
  Dumbbell,
  Moon,
  Sparkles,
  Info,
} from 'lucide-react';
import { PipelineEvent } from '../types/pipeline';
import { formatRelativeTime, formatExactDateTime } from '../utils/formatters';

interface LiveEventFeedProps {
  events: PipelineEvent[];
  onClear: () => void;
}

export const LiveEventFeed: React.FC<LiveEventFeedProps> = ({ events, onClear }) => {
  const [expandedId, setExpandedId] = useState<string | number | null>(null);
  const [filterType, setFilterType] = useState<string>('ALL');

  const toggleExpand = (id: string | number) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const getEventBadge = (eventType: string) => {
    switch (eventType) {
      case 'FILE_PROCESSED':
        return {
          icon: <FileCheck className="w-3.5 h-3.5" />,
          color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
        };
      case 'FILE_DETECTED':
        return {
          icon: <Sparkles className="w-3.5 h-3.5" />,
          color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
        };
      case 'workout_logged':
        return {
          icon: <Dumbbell className="w-3.5 h-3.5" />,
          color: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
        };
      case 'sleep_summary_ready':
        return {
          icon: <Moon className="w-3.5 h-3.5" />,
          color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
        };
      case 'PIPELINE_ERROR':
        return {
          icon: <AlertTriangle className="w-3.5 h-3.5" />,
          color: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
        };
      default:
        return {
          icon: <Info className="w-3.5 h-3.5" />,
          color: 'text-slate-400 bg-slate-800 border-slate-700',
        };
    }
  };

  const filteredEvents = events.filter((ev) => {
    if (filterType === 'ALL') return true;
    return ev.eventType === filterType;
  });

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col h-[560px]">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Radio className="w-4 h-4 text-cyan-400" />
            <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-cyan-400 rounded-full animate-ping" />
          </div>
          <h2 className="text-sm font-bold text-white tracking-tight">Pub/Sub Event Bus Stream</h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
            {filteredEvents.length} events
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter Dropdown */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50"
          >
            <option value="ALL">All Events</option>
            <option value="FILE_PROCESSED">FILE_PROCESSED</option>
            <option value="FILE_DETECTED">FILE_DETECTED</option>
            <option value="workout_logged">workout_logged</option>
            <option value="sleep_summary_ready">sleep_summary_ready</option>
            <option value="PIPELINE_ERROR">PIPELINE_ERROR</option>
          </select>

          {/* Clear button */}
          <button
            onClick={onClear}
            title="Clear event log"
            className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-slate-800 rounded transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Stream list */}
      <div className="flex-1 overflow-y-auto mt-3 space-y-2 pr-1">
        {filteredEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs py-12">
            <Radio className="w-8 h-8 mb-2 stroke-1 opacity-40 text-slate-600" />
            <span>Waiting for stream events...</span>
            <span className="text-[10px] text-slate-600 mt-1">
              Events emitted by ETL scripts or the test simulator will show here live.
            </span>
          </div>
        ) : (
          filteredEvents.map((ev, index) => {
            const id = ev.id ?? `evt-${index}`;
            const badge = getEventBadge(ev.eventType);
            const isExpanded = expandedId === id;

            return (
              <div
                key={id}
                className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 transition-all hover:border-slate-700/80"
              >
                <div
                  onClick={() => toggleExpand(id)}
                  className="flex items-center justify-between cursor-pointer gap-2"
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span
                      className={`flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded border ${badge.color}`}
                    >
                      {badge.icon}
                      <span>{ev.eventType}</span>
                    </span>

                    <span
                      className="text-xs text-slate-300 font-mono truncate"
                      title={JSON.stringify(ev.payload)}
                    >
                      {typeof ev.payload === 'object' && ev.payload !== null
                        ? Object.entries(ev.payload)
                            .slice(0, 2)
                            .map(([k, v]) => `${k}=${String(v)}`)
                            .join(', ')
                        : String(ev.payload)}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className="text-[11px] text-slate-500 cursor-help"
                      title={formatExactDateTime(ev.timestamp)}
                    >
                      {formatRelativeTime(ev.timestamp)}
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                    )}
                  </div>
                </div>

                {/* Expanded Payload Inspector */}
                {isExpanded && (
                  <div className="mt-3 pt-2 border-t border-slate-800/80">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 font-semibold">
                      Raw Event Payload
                    </div>
                    <pre className="p-2.5 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-cyan-300 overflow-x-auto">
                      {JSON.stringify(ev, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
