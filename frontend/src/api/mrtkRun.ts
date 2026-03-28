/**
 * API client for mrtk run (real-time processing) endpoints
 */

const API_BASE = '/api/mrtk-run';

export interface MrtkRunStartRequest {
  config: Record<string, unknown>;
  streams: Record<string, unknown>;
}

export interface MrtkRunResponse {
  status: string;
  message: string;
}

export interface MrtkRunStatusResponse {
  running: boolean;
  status: Record<string, unknown>;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

export const mrtkRunApi = {
  start: async (request: MrtkRunStartRequest): Promise<MrtkRunResponse> => {
    const response = await fetch(`${API_BASE}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return handleResponse<MrtkRunResponse>(response);
  },

  stop: async (): Promise<MrtkRunResponse> => {
    const response = await fetch(`${API_BASE}/stop`, { method: 'POST' });
    return handleResponse<MrtkRunResponse>(response);
  },

  status: async (): Promise<MrtkRunStatusResponse> => {
    const response = await fetch(`${API_BASE}/status`);
    return handleResponse<MrtkRunStatusResponse>(response);
  },

  /**
   * Connect to the WebSocket for real-time status updates.
   * Returns the WebSocket instance.
   */
  connectWs: (): WebSocket => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return new WebSocket(`${protocol}//${host}${API_BASE}/ws`);
  },
};
