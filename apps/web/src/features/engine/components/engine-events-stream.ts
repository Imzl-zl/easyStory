"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import type { ExecutionLogView } from "@/lib/api/types";
import { getAuthToken } from "@/lib/stores/auth-store";
import {
  buildSystemExecutionLog,
  consumeWorkflowEvents,
  isClientStreamError,
  mergeExecutionLogs,
  resolveClientStreamErrorMessage,
  upsertExecutionLog,
} from "@/features/engine/components/engine-events-stream-support";

const QUIET_RECONNECT_DELAY_MS = 250;
const ERROR_RECONNECT_DELAY_MS = 2000;
const EMPTY_WORKFLOW_SESSION: WorkflowSession = { sessionId: 0, workflowId: "" };

type WorkflowEventsConnectionState = "idle" | "connecting" | "connected" | "reconnecting";

type WorkflowSession = {
  sessionId: number;
  workflowId: string;
};

type WorkflowBoundState<T> = {
  sessionId: number;
  value: T;
  workflowId: string;
};

type WorkflowEventsStreamState = {
  clientErrorMessage: string | null;
  connectionState: WorkflowEventsConnectionState;
  endSignal: number;
  logs: ExecutionLogView[];
  reconnectSignal: number;
};

export function useWorkflowEventsStream({
  workflowId,
  enabled,
  snapshotLogs,
}: {
  workflowId: string;
  enabled: boolean;
  snapshotLogs: ExecutionLogView[];
}): WorkflowEventsStreamState {
  const sessionIdRef = useRef(0);
  const [localLogs, setLocalLogs] =
    useState<WorkflowBoundState<ExecutionLogView[]>>(createWorkflowBoundState([]));
  const [connectionState, setConnectionState] =
    useState<WorkflowBoundState<WorkflowEventsConnectionState>>(createWorkflowBoundState("idle"));
  const [clientError, setClientError] =
    useState<WorkflowBoundState<string | null>>(createWorkflowBoundState(null));
  const [reconnectSignal, setReconnectSignal] =
    useState<WorkflowBoundState<number>>(createWorkflowBoundState(0));
  const [endSignal, setEndSignal] = useState<WorkflowBoundState<number>>(createWorkflowBoundState(0));

  useEffect(() => {
    if (!enabled || !workflowId) {
      return;
    }

    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let controller: AbortController | null = null;
    let hadConnectionError = false;
    const sessionId = sessionIdRef.current + 1;
    sessionIdRef.current = sessionId;
    const session = { sessionId, workflowId };

    const updateConnectionState = (value: WorkflowEventsConnectionState) => {
      setConnectionState({ ...session, value });
    };

    const appendExecutionLog = (log: ExecutionLogView) => {
      setLocalLogs((current) => ({
        ...session,
        value:
          current.workflowId === workflowId && current.sessionId === sessionId
            ? upsertExecutionLog(current.value, log)
            : upsertExecutionLog([], log),
      }));
    };

    const cleanupStream = () => {
      controller?.abort();
      controller = null;
      if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    const scheduleReconnect = (delayMs: number, state: WorkflowEventsConnectionState) => {
      if (cancelled) {
        return;
      }
      updateConnectionState(state);
      reconnectTimer = setTimeout(() => {
        void connect();
      }, delayMs);
    };

    const connect = async () => {
      const token = getAuthToken();
      if (!token || cancelled) {
        updateConnectionState("idle");
        return;
      }

      controller = new AbortController();
      updateConnectionState(hadConnectionError ? "reconnecting" : "connecting");
      setClientError({ ...session, value: null });

      try {
        const outcome = await consumeWorkflowEvents({
          workflowId,
          token,
          signal: controller.signal,
          onExecutionLog: appendExecutionLog,
          onOpen: () => {
            updateConnectionState("connected");
            setClientError({ ...session, value: null });
            if (!hadConnectionError) {
              return;
            }
            hadConnectionError = false;
            setReconnectSignal({ ...session, value: Date.now() });
            appendExecutionLog(
              buildSystemExecutionLog(workflowId, "实时连接已恢复，已重新接入 workflow events。"),
            );
          },
        });

        if (cancelled) {
          return;
        }
        if (outcome === "ended") {
          updateConnectionState("idle");
          setEndSignal({ ...session, value: Date.now() });
          return;
        }
        scheduleReconnect(QUIET_RECONNECT_DELAY_MS, "connecting");
      } catch (error) {
        if (cancelled || controller.signal.aborted) {
          return;
        }
        if (isClientStreamError(error)) {
          const message = resolveClientStreamErrorMessage(error);
          updateConnectionState("idle");
          setClientError({ ...session, value: message });
          appendExecutionLog(
            buildSystemExecutionLog(workflowId, message),
          );
          return;
        }
        hadConnectionError = true;
        scheduleReconnect(ERROR_RECONNECT_DELAY_MS, "reconnecting");
      }
    };

    void connect();

    return () => {
      cancelled = true;
      cleanupStream();
    };
  }, [enabled, workflowId]);
  const activeSession = resolveActiveWorkflowSession(enabled, workflowId, connectionState);

  const logs = useMemo(
    () =>
      mergeExecutionLogs(
        snapshotLogs,
        matchesWorkflowSession(localLogs, activeSession) ? localLogs.value : [],
      ),
    [activeSession, localLogs, snapshotLogs],
  );

  return {
    clientErrorMessage: matchesWorkflowSession(clientError, activeSession) ? clientError.value : null,
    connectionState: enabled && matchesWorkflowSession(connectionState, activeSession) ? connectionState.value : "idle",
    endSignal: matchesWorkflowSession(endSignal, activeSession) ? endSignal.value : 0,
    logs,
    reconnectSignal: matchesWorkflowSession(reconnectSignal, activeSession) ? reconnectSignal.value : 0,
  };
}

function createWorkflowBoundState<T>(value: T): WorkflowBoundState<T> {
  return {
    ...EMPTY_WORKFLOW_SESSION,
    value,
  };
}

function matchesWorkflowSession<T>(
  state: WorkflowBoundState<T>,
  session: WorkflowSession,
): boolean {
  return state.workflowId === session.workflowId && state.sessionId === session.sessionId;
}

function resolveActiveWorkflowSession(
  enabled: boolean,
  workflowId: string,
  connectionState: WorkflowBoundState<WorkflowEventsConnectionState>,
): WorkflowSession {
  if (!enabled || connectionState.workflowId !== workflowId) {
    return EMPTY_WORKFLOW_SESSION;
  }
  return {
    sessionId: connectionState.sessionId,
    workflowId,
  };
}

export function resolveWorkflowEventsBanner(
  connectionState: WorkflowEventsConnectionState,
): string | null {
  if (connectionState !== "reconnecting") {
    return null;
  }
  return "实时连接已断开，正在重试。";
}

export function useWorkflowEventsQuerySync({
  workflowId,
  reconnectSignal,
  endSignal,
}: {
  workflowId: string;
  reconnectSignal: number;
  endSignal: number;
}): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    const refreshSignal = Math.max(reconnectSignal, endSignal);
    if (!workflowId || refreshSignal === 0) {
      return;
    }
    queryClient.invalidateQueries({ queryKey: ["workflow-observability", workflowId] });
    queryClient.invalidateQueries({ queryKey: ["workflow", workflowId] });
  }, [endSignal, queryClient, reconnectSignal, workflowId]);
}
