import { useState, useEffect, useCallback, useRef } from 'react';
import {
  PipelineStatusResponse,
  PipelineEvent,
  ConnectionStatus,
  HealthDataType,
  CategoryTelemetry,
} from '../types/pipeline';

interface UsePipelineStreamReturn {
  telemetry: PipelineStatusResponse | null;
  events: PipelineEvent[];
  connectionStatus: ConnectionStatus;
  lastHeartbeat: Date | null;
  reconnect: () => void;
  publishEvent: (eventType: string, payload: Record<string, unknown>) => Promise<boolean>;
  clearEvents: () => void;
  isLoading: boolean;
  error: string | null;
}

const MAX_EVENT_LOG_SIZE = 100;

export function usePipelineStream(): UsePipelineStreamReturn {
  const [telemetry, setTelemetry] = useState<PipelineStatusResponse | null>(null);
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');
  const [lastHeartbeat, setLastHeartbeat] = useState<Date | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const pulseTimersRef = useRef<Map<HealthDataType, NodeJS.Timeout>>(new Map());

  // Trigger brief visual pulse on category card when an event arrives
  const triggerCategoryPulse = useCallback((category: HealthDataType) => {
    setTelemetry((prev) => {
      if (!prev || !prev.categories[category]) return prev;
      const updatedCategory: CategoryTelemetry = {
        ...prev.categories[category]!,
        isPulsing: true,
        lastEventAt: new Date().toISOString(),
      };
      return {
        ...prev,
        categories: {
          ...prev.categories,
          [category]: updatedCategory,
        },
      };
    });

    // Clear existing timer if any
    const existing = pulseTimersRef.current.get(category);
    if (existing) clearTimeout(existing);

    const timer = setTimeout(() => {
      setTelemetry((prev) => {
        if (!prev || !prev.categories[category]) return prev;
        const resetCategory: CategoryTelemetry = {
          ...prev.categories[category]!,
          isPulsing: false,
        };
        return {
          ...prev,
          categories: {
            ...prev.categories,
            [category]: resetCategory,
          },
        };
      });
    }, 2500);

    pulseTimersRef.current.set(category, timer);
  }, []);

  // Fetch initial state via REST as reliable baseline
  const fetchInitialData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [statusRes, eventsRes] = await Promise.all([
        fetch('/api/pipeline/status'),
        fetch('/api/pipeline/events?limit=30'),
      ]);

      if (statusRes.ok) {
        const statusData: PipelineStatusResponse = await statusRes.json();
        setTelemetry(statusData);
      } else {
        throw new Error(`Failed to load pipeline status (${statusRes.status})`);
      }

      if (eventsRes.ok) {
        const eventsData = await eventsRes.json();
        if (Array.isArray(eventsData.events)) {
          setEvents(eventsData.events);
        }
      }
    } catch (err) {
      console.warn('REST initial fetch warning:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect to backend');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Connect to SSE stream
  const connectSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setConnectionStatus('connecting');
    const es = new EventSource('/api/pipeline/stream');
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnectionStatus('connected');
      setError(null);
      setLastHeartbeat(new Date());
    };

    es.onerror = () => {
      setConnectionStatus('error');
      // EventSource auto-retries, but we keep track of status
    };

    // Generic message handler
    es.onmessage = (e) => {
      setLastHeartbeat(new Date());
      try {
        const rawData = JSON.parse(e.data);
        if (rawData.eventType) {
          setEvents((prev) => [rawData, ...prev.slice(0, MAX_EVENT_LOG_SIZE - 1)]);
        }
      } catch {
        // Heartbeat or text message
      }
    };

    // Initial state event
    es.addEventListener('INITIAL_STATE', (e: MessageEvent) => {
      try {
        const parsed: PipelineStatusResponse = JSON.parse(e.data);
        setTelemetry(parsed);
        setLastHeartbeat(new Date());
        setIsLoading(false);
      } catch (err) {
        console.error('Failed to parse INITIAL_STATE:', err);
      }
    });

    // Telemetry updates
    es.addEventListener('TELEMETRY_UPDATE', (e: MessageEvent) => {
      try {
        const parsed: PipelineStatusResponse = JSON.parse(e.data);
        setTelemetry((prev) => {
          if (!prev) return parsed;
          // Preserve any active local pulsing flags
          const mergedCategories = { ...parsed.categories };
          (Object.keys(mergedCategories) as HealthDataType[]).forEach((cat) => {
            if (prev.categories[cat]?.isPulsing) {
              mergedCategories[cat] = {
                ...mergedCategories[cat]!,
                isPulsing: true,
              };
            }
          });
          return { ...parsed, categories: mergedCategories };
        });
        setLastHeartbeat(new Date());
      } catch (err) {
        console.error('Failed to parse TELEMETRY_UPDATE:', err);
      }
    });

    // Custom domain events
    const domainEvents = [
      'FILE_DETECTED',
      'FILE_PROCESSED',
      'workout_logged',
      'sleep_summary_ready',
      'PIPELINE_ERROR',
    ];

    domainEvents.forEach((evtName) => {
      es.addEventListener(evtName, (e: MessageEvent) => {
        try {
          const parsed = JSON.parse(e.data);
          const newEvent: PipelineEvent = {
            id: parsed.id || Date.now(),
            eventType: evtName,
            payload: parsed.payload || parsed,
            timestamp: parsed.timestamp || new Date().toISOString(),
            status: parsed.status || 'success',
          };

          setEvents((prev) => [newEvent, ...prev.slice(0, MAX_EVENT_LOG_SIZE - 1)]);

          // If event has an associated category, pulse it
          if (parsed.payload?.category) {
            triggerCategoryPulse(parsed.payload.category as HealthDataType);
          } else if (evtName === 'workout_logged') {
            triggerCategoryPulse('steps');
          } else if (evtName === 'sleep_summary_ready') {
            triggerCategoryPulse('sleep');
          }
        } catch (err) {
          console.error(`Failed to handle SSE event ${evtName}:`, err);
        }
      });
    });
  }, [triggerCategoryPulse]);

  useEffect(() => {
    fetchInitialData();
    connectSSE();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      pulseTimersRef.current.forEach((timer) => clearTimeout(timer));
    };
  }, [fetchInitialData, connectSSE]);

  const reconnect = useCallback(() => {
    fetchInitialData();
    connectSSE();
  }, [fetchInitialData, connectSSE]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  const publishEvent = useCallback(
    async (eventType: string, payload: Record<string, unknown>): Promise<boolean> => {
      try {
        const res = await fetch('/api/pipeline/publish', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ eventType, payload }),
        });
        return res.ok;
      } catch (err) {
        console.error('Failed to publish event:', err);
        return false;
      }
    },
    []
  );

  return {
    telemetry,
    events,
    connectionStatus,
    lastHeartbeat,
    reconnect,
    publishEvent,
    clearEvents,
    isLoading,
    error,
  };
}
