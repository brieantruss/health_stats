# Health Stats Operations Dashboard (React + TypeScript + Pub/Sub)

A real-time ETL operations and observability dashboard built with **React**, **TypeScript**, **Vite**, and **Tailwind CSS**.

It connects via **Server-Sent Events (SSE)** and **Pub/Sub** to the health stats backend to display:
- Real-time ingestion telemetry for all 13 health data categories.
- Total processed files and storage volume per category.
- **Latest file name and timestamp** per category with relative and exact date formatting.
- Live streaming **Pub/Sub event bus** feed (`FILE_PROCESSED`, `FILE_DETECTED`, `workout_logged`, `sleep_summary_ready`, `PIPELINE_ERROR`).
- Built-in **Pub/Sub Event Simulator** to test real-time event broadcasting and card pulsing.

---

## TypeScript Architecture Highlights

1. **Strict Type Checking:**
   - Full TypeScript configuration with `strict: true`, `noUncheckedIndexedAccess: true`.
2. **Discriminated Union Event Bus:**
   - `PipelineEvent` in `src/types/pipeline.ts` uses discriminated unions on `eventType` for type-safe event handling.
3. **Custom React Hook (`usePipelineStream`):**
   - Handles `EventSource` connection lifecycle, automatic reconnects, REST baseline fallback, and real-time state reduction.
4. **Category Metadata Contracts:**
   - Strongly typed `Record<HealthDataType, CategoryTelemetry>` ensuring every data type (`heart_rate`, `sleep`, `locations`, etc.) has strict type guarantees across the UI.

---

## Getting Started

### 1. Install Dependencies
```bash
cd ops_dashboard
npm install
```

### 2. Start the Backend API (Flask)
From repository root:
```bash
python fitness_api/api_app.py
```
*(Runs on port 5001)*

### 3. Start the Frontend Dev Server
From `ops_dashboard/`:
```bash
npm run dev
```
*(Opens on `http://localhost:5173` with proxy to `:5001`)*

### 4. Build for Production
```bash
npm run build
```
*(Runs TypeScript type check `tsc` followed by Vite bundle generation into `dist/`)*
