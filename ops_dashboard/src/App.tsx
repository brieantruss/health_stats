import { useState } from 'react';
import { Header } from './components/Header';
import { MetricsOverview } from './components/MetricsOverview';
import { CategoryGrid } from './components/CategoryGrid';
import { LiveEventFeed } from './components/LiveEventFeed';
import { DevEventSimulator } from './components/DevEventSimulator';
import { usePipelineStream } from './hooks/usePipelineStream';
import { AlertCircle } from 'lucide-react';

export function App() {
  const {
    telemetry,
    events,
    connectionStatus,
    lastHeartbeat,
    reconnect,
    publishEvent,
    clearEvents,
    error,
  } = usePipelineStream();

  const [isSimulatorOpen, setIsSimulatorOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Navigation */}
      <Header
        connectionStatus={connectionStatus}
        lastHeartbeat={lastHeartbeat}
        onReconnect={reconnect}
        onOpenSimulator={() => setIsSimulatorOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Error Banner if REST or Stream disconnected */}
        {error && (
          <div className="flex items-center justify-between p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
            <button
              onClick={reconnect}
              className="px-2.5 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 font-medium transition-colors"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Top Metric Cards */}
        <MetricsOverview telemetry={telemetry} />

        {/* Main 2-Column Layout: Left Category Telemetry / Right Live PubSub Event Bus */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* Left 2 Cols: Category Grid / Table with Latest Files & Times */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-white tracking-tight">
                  Category Ingestion Telemetry
                </h2>
                <p className="text-xs text-slate-400">
                  Total files, volume, and most recent file names per health data stream
                </p>
              </div>
            </div>

            <CategoryGrid telemetry={telemetry} />
          </div>

          {/* Right 1 Col: Live Pub/Sub Event Stream Ticker */}
          <div className="lg:col-span-1">
            <LiveEventFeed events={events} onClear={clearEvents} />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-center text-xs text-slate-500">
        Health Stats ETL Operations • React + TypeScript + Vite + Pub/Sub Event Bus
      </footer>

      {/* Dev Pub/Sub Event Simulator Modal */}
      <DevEventSimulator
        isOpen={isSimulatorOpen}
        onClose={() => setIsSimulatorOpen(false)}
        onPublish={publishEvent}
      />
    </div>
  );
}

export default App;
