/**
 * WebSocket hook for real-time job progress and log updates.
 */
"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { WSEvent, WSProgressEvent, WSStatusEvent, WSLogEvent, JobStatus, LogEntry } from "@/types";
import { WS_URL } from "@/lib/api";

interface JobProgress {
  progress_pct: number;
  scraped_pages: number;
  total_pages: number;
  items_found: number;
  current_url: string;
  elapsed_seconds: number;
}

interface UseJobWebSocketReturn {
  progress: JobProgress | null;
  status: JobStatus | null;
  logs: LogEntry[];
  isConnected: boolean;
}

export function useJobWebSocket(jobId: string | null): UseJobWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [progress, setProgress] = useState<JobProgress | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    if (!jobId) return;

    const ws = new WebSocket(`${WS_URL}/ws/${jobId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Reconnect after 3s unless job is complete
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          connect();
        }
      }, 3000);
    };

    ws.onmessage = (event) => {
      try {
        const data: WSEvent = JSON.parse(event.data);
        if (data.type === "progress") {
          setProgress(data as WSProgressEvent);
        } else if (data.type === "status") {
          const statusEvent = data as WSStatusEvent;
          setStatus(statusEvent.status);
          // Stop reconnecting on terminal states
          if (["completed", "failed", "cancelled"].includes(statusEvent.status)) {
            ws.close();
          }
        } else if (data.type === "log") {
          const logEvent = data as WSLogEvent;
          setLogs((prev) => [
            { ...logEvent, timestamp: new Date().toISOString() },
            ...prev.slice(0, 499), // Keep last 500 logs
          ]);
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onerror = () => {
      setIsConnected(false);
    };
  }, [jobId]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { progress, status, logs, isConnected };
}
