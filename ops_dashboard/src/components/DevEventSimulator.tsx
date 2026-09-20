import React, { useState } from 'react';
import { Radio, X, Send, CheckCircle2 } from 'lucide-react';
import { HealthDataType } from '../types/pipeline';

interface DevEventSimulatorProps {
  isOpen: boolean;
  onClose: () => void;
  onPublish: (eventType: string, payload: Record<string, unknown>) => Promise<boolean>;
}

export const DevEventSimulator: React.FC<DevEventSimulatorProps> = ({
  isOpen,
  onClose,
  onPublish,
}) => {
  const [selectedType, setSelectedType] = useState<string>('FILE_PROCESSED');
  const [category, setCategory] = useState<HealthDataType>('heart_rate');
  const [fileName, setFileName] = useState('Heart rate 2026.09.20 Samsung Health.csv');
  const [rowCount, setRowCount] = useState(1440);
  const [exercise, setExercise] = useState('pushup');
  const [reps, setReps] = useState(25);
  const [sleepHours, setSleepHours] = useState(7.8);
  const [errorMessage, setErrorMessage] = useState('BigQuery load rate limit exceeded');
  const [customJson, setCustomJson] = useState('{\n  "custom_key": "health_data_value"\n}');
  const [isSending, setIsSending] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSend = async () => {
    setIsSending(true);
    setFeedback(null);
    let payload: Record<string, unknown> = {};

    try {
      if (selectedType === 'FILE_PROCESSED') {
        payload = {
          category,
          fileName: fileName.trim() || `mock_${category}_${Date.now()}.csv`,
          rowCount: Number(rowCount),
          destination: 'mysql',
          timestamp: new Date().toISOString(),
        };
      } else if (selectedType === 'FILE_DETECTED') {
        payload = {
          category,
          fileName: fileName.trim() || `raw_${category}_${Date.now()}.csv`,
          source: 'samsung_health_export',
          timestamp: new Date().toISOString(),
        };
      } else if (selectedType === 'workout_logged') {
        payload = {
          exercise,
          reps: Number(reps),
          timestamp: new Date().toISOString(),
        };
      } else if (selectedType === 'sleep_summary_ready') {
        payload = {
          total_hours: Number(sleepHours),
          timestamp: new Date().toISOString(),
        };
      } else if (selectedType === 'PIPELINE_ERROR') {
        payload = {
          category,
          stage: 'load_bigquery',
          message: errorMessage,
          timestamp: new Date().toISOString(),
        };
      } else {
        payload = JSON.parse(customJson);
      }

      const success = await onPublish(selectedType, payload);
      if (success) {
        setFeedback('Event broadcasted to Pub/Sub stream!');
        setTimeout(() => setFeedback(null), 3000);
      } else {
        setFeedback('Failed to publish event to server.');
      }
    } catch (err) {
      setFeedback(`Invalid JSON or error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2 text-cyan-400">
            <Radio className="w-5 h-5 animate-pulse" />
            <h2 className="text-base font-bold text-white tracking-tight">
              Pub/Sub Event Simulator
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form controls */}
        <div className="mt-4 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Event Type
            </label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="FILE_PROCESSED">FILE_PROCESSED (ETL Completed)</option>
              <option value="FILE_DETECTED">FILE_DETECTED (New File Ingestion)</option>
              <option value="workout_logged">workout_logged (Exercise Logged)</option>
              <option value="sleep_summary_ready">sleep_summary_ready (Sleep Analyzed)</option>
              <option value="PIPELINE_ERROR">PIPELINE_ERROR (Alert)</option>
              <option value="CUSTOM">CUSTOM JSON</option>
            </select>
          </div>

          {(selectedType === 'FILE_PROCESSED' ||
            selectedType === 'FILE_DETECTED' ||
            selectedType === 'PIPELINE_ERROR') && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as HealthDataType)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {[
                  'blood_pressure',
                  'cycling',
                  'heart_rate',
                  'locations',
                  'oxygen',
                  'running',
                  'shootaround',
                  'sleep',
                  'steps',
                  'swimming',
                  'vo2max',
                  'walking',
                  'weather',
                ].map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>
          )}

          {(selectedType === 'FILE_PROCESSED' || selectedType === 'FILE_DETECTED') && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Simulated File Name
              </label>
              <input
                type="text"
                value={fileName}
                onChange={(e) => setFileName(e.target.value)}
                placeholder="e.g. Heart rate 2026.09.20 Samsung Health.csv"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>
          )}

          {selectedType === 'FILE_PROCESSED' && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Rows Processed
              </label>
              <input
                type="number"
                value={rowCount}
                onChange={(e) => setRowCount(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>
          )}

          {selectedType === 'workout_logged' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Exercise
                </label>
                <input
                  type="text"
                  value={exercise}
                  onChange={(e) => setExercise(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Reps
                </label>
                <input
                  type="number"
                  value={reps}
                  onChange={(e) => setReps(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          )}

          {selectedType === 'sleep_summary_ready' && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Total Sleep Hours
              </label>
              <input
                type="number"
                step="0.1"
                value={sleepHours}
                onChange={(e) => setSleepHours(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          )}

          {selectedType === 'PIPELINE_ERROR' && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Error Message
              </label>
              <input
                type="text"
                value={errorMessage}
                onChange={(e) => setErrorMessage(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-rose-300 focus:outline-none focus:border-rose-500"
              />
            </div>
          )}

          {selectedType === 'CUSTOM' && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Custom JSON Payload
              </label>
              <textarea
                value={customJson}
                onChange={(e) => setCustomJson(e.target.value)}
                rows={4}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 font-mono text-xs text-cyan-300 focus:outline-none focus:border-cyan-500"
              />
            </div>
          )}
        </div>

        {/* Feedback message */}
        {feedback && (
          <div className="mt-3 flex items-center gap-2 p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{feedback}</span>
          </div>
        )}

        {/* Actions */}
        <div className="mt-6 flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSend}
            disabled={isSending}
            className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-cyan-500/20 transition-all disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{isSending ? 'Publishing...' : 'Emit Event'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
