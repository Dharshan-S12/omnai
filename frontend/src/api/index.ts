export const API_URL = "http://localhost:8000";

export interface TaskStep {
  id: string;
  task_id: string;
  step_number: number;
  description: string;
  tool_called: string | null;
  tool_result: any;
  created_at: string;
}

export interface TaskItem {
  id: string;
  task_type: "ocr" | "text_gen" | "doc_gen" | "code_exec" | "cross_doc_query";
  status: "pending" | "running" | "done" | "failed";
  input_ref: string;
  output_ref: string | null;
  source_task_id?: string | null;
  created_at: string;
  updated_at?: string | null;
  steps?: TaskStep[];
}

export interface NetworkConnection {
  pid: number;
  process_name: string;
  local_address: string;
  remote_address: string;
  remote_ip: string;
  remote_port: number | null;
  status: string;
  type: string;
  classification: "local" | "external";
  timestamp: string;
}

export interface MonitoredProcess {
  pid: number;
  name: string;
  status: string;
  created: string;
}

export interface NetworkMonitorData {
  is_air_gapped: boolean;
  total_external_connections_seen: number;
  total_local_connections_seen: number;
  monitored_processes_count: number;
  monitored_processes: MonitoredProcess[];
  active_connections: NetworkConnection[];
  recent_log: NetworkConnection[];
  timestamp: string;
}

export interface HealthStatus {
  status: "ok" | "degraded" | "error";
  db: "connected" | "unreachable";
  ollama_status: "connected" | "unreachable";
  ollama_models?: string[];
}

export const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/files/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) throw new Error("Failed to upload file");
  return response.json();
};

export const createTask = async (
  task_type: string,
  input_ref: string,
  source_task_id?: string | null
): Promise<TaskItem> => {
  const payload: Record<string, any> = { task_type, input_ref };
  if (source_task_id) {
    payload.source_task_id = source_task_id;
  }

  const response = await fetch(`${API_URL}/tasks/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Failed to create task: ${err}`);
  }
  return response.json();
};

export const createAutoTask = async (
  prompt: string,
  filePath?: string | null,
  source_task_id?: string | null
): Promise<TaskItem> => {
  const payload: Record<string, any> = { prompt };
  if (filePath) {
    payload.file_path = filePath;
  }
  if (source_task_id) {
    payload.source_task_id = source_task_id;
  }

  const response = await fetch(`${API_URL}/tasks/auto`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Failed to create auto task: ${err}`);
  }
  return response.json();
};

export const fetchTasks = async (): Promise<TaskItem[]> => {
  const response = await fetch(`${API_URL}/tasks/`);
  if (!response.ok) throw new Error("Failed to fetch tasks");
  return response.json();
};

export const fetchTaskDetails = async (id: string): Promise<TaskItem> => {
  const response = await fetch(`${API_URL}/tasks/${id}`);
  if (!response.ok) throw new Error("Failed to fetch task details");
  return response.json();
};

export const fetchNetworkStatus = async (): Promise<NetworkMonitorData> => {
  const response = await fetch(`${API_URL}/monitor/connections`);
  if (!response.ok) throw new Error("Failed to fetch network monitor status");
  return response.json();
};

export const fetchHealthStatus = async (): Promise<HealthStatus> => {
  const response = await fetch(`${API_URL}/health`);
  if (!response.ok) throw new Error("Failed to fetch health status");
  return response.json();
};

export const getDocxDownloadUrl = (taskId: string) => `${API_URL}/tasks/${taskId}/output/docx`;
export const getTextDownloadUrl = (taskId: string) => `${API_URL}/tasks/${taskId}/output`;
