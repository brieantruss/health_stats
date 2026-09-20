import React from 'react';
import { Activity, RefreshCw, Radio, Wifi, WifiOff } from 'lucide-react';
import { ConnectionStatus } from '../types/pipeline';

interface HeaderProps {
  connectionStatus: ConnectionStatus;
  lastHeartbeat: Date | null;
  onReconnect: () => void;
  onOpenSimulator: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  connectionStatus,
  lastHeartbeat,
  onReconnect,
  onOpenSimulator,
}) => {
  const getStatusBadge = () => {
    switch (connectionStatus) {
      case 'connected':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <Wifi className="w-3.5 h-3.5" />
            <span>SSE Stream Live</span>
          </div>
        );
      case 'connecting':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-medium">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <span>Connecting...</span>
          </div>
        );
      case 'disconnected':
      case 'error':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-medium">
            <WifiOff className="w-3.5 h-3.5" />
            <span>Stream Offline</span>
          </div>
        );
    }
  };

  return (
    <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
        {/* Title & Brand */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/20">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-white tracking-tight">
                Health Pipeline Operations
              </h1>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 tracking-wider">
                TypeScript + Pub/Sub
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Real-time ETL telemetry, file ingestion tracking & event stream
            </p>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-3">
          {getStatusBadge()}

          {lastHeartbeat && (
            <span className="hidden md:inline-block text-xs text-slate-500 font-mono">
              Ping: {lastHeartbeat.toLocaleTimeString()}
            </span>
          )}

          <button
            onClick={onReconnect}
            title="Refresh stream & telemetry"
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors border border-slate-700/50"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={onOpenSimulator}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-xs font-medium transition-all shadow-sm"
          >
            <Radio className="w-3.5 h-3.5" />
            <span>Emit Test Event</span>
          </button>
        </div>
      </div>
    </header>
  );
};
