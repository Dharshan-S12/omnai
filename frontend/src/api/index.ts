export const API_URL = "http://localhost:8000";

// Role Management (Operator vs Supervisor)
export type UserRole = "operator" | "supervisor";

export const getUserRole = (): UserRole => {
  const stored = localStorage.getItem("mrpl_user_role");
  return (stored === "operator" || stored === "supervisor") ? stored : "supervisor";
};

export const setUserRole = (role: UserRole) => {
  localStorage.setItem("mrpl_user_role", role);
};

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
  status: "pending" | "running" | "done" | "failed" | "pending_approval" | "rejected";
  input_ref: string;
  output_ref: string | null;
  confidence_score?: number | null;
  source_task_id?: string | null;
  created_at: string;
  updated_at?: string | null;
  steps?: TaskStep[];
}

export interface DisambiguationOption {
  task_type: string;
  label: string;
  description: string;
  model_name: string;
}

export interface DisambiguationResponse {
  is_disambiguation: true;
  prompt: string;
  file_path?: string | null;
  confidence: number;
  message: string;
  options: DisambiguationOption[];
  suggested_task_type: string;
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

export interface DBHealthInfo {
  active_backend: "postgresql" | "sqlite";
  is_fallback: boolean;
  fallback_timestamp?: string | null;
  fallback_reason?: string | null;
  integrity_mode: string;
  banner_message?: string | null;
}

export interface HealthStatus {
  status: "ok" | "degraded" | "error";
  db: "connected" | "unreachable";
  db_health?: DBHealthInfo;
  ollama_status: "connected" | "unreachable";
  ollama_models?: string[];
  router_ready?: boolean;
  active_models_count?: number;
}

export interface AuditVerifyResponse {
  verified: boolean;
  total_records: number;
  latest_hash?: string | null;
  tampered_sequence?: number | null;
  error_message?: string | null;
  checked_at: string;
}

export const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/files/upload`, {
    method: "POST",
    headers: {
      "X-User-Role": getUserRole()
    },
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
      "X-User-Role": getUserRole()
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
  source_task_id?: string | null,
  confirmed_intent?: string | null
): Promise<TaskItem | DisambiguationResponse> => {
  const payload: Record<string, any> = { prompt };
  if (filePath) {
    payload.file_path = filePath;
  }
  if (source_task_id) {
    payload.source_task_id = source_task_id;
  }
  if (confirmed_intent) {
    payload.confirmed_intent = confirmed_intent;
  }

  const response = await fetch(`${API_URL}/tasks/auto`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": getUserRole()
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
  const response = await fetch(`${API_URL}/tasks/`, {
    headers: { "X-User-Role": getUserRole() }
  });
  if (!response.ok) throw new Error("Failed to fetch tasks");
  return response.json();
};

export const fetchTaskDetails = async (id: string): Promise<TaskItem> => {
  const response = await fetch(`${API_URL}/tasks/${id}`, {
    headers: { "X-User-Role": getUserRole() }
  });
  if (!response.ok) throw new Error("Failed to fetch task details");
  return response.json();
};

export const approveTask = async (
  taskId: string,
  payload: { approved: boolean; reviewer_notes?: string; reviewer_name?: string }
): Promise<TaskItem> => {
  const response = await fetch(`${API_URL}/tasks/${taskId}/approve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": getUserRole()
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Failed to process approval decision: ${err}`);
  }
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

export const fetchAuditVerification = async (): Promise<AuditVerifyResponse> => {
  const response = await fetch(`${API_URL}/audit/verify`);
  if (!response.ok) throw new Error("Failed to fetch audit verification");
  return response.json();
};

export const getDocxDownloadUrl = (taskId: string) => `${API_URL}/tasks/${taskId}/output/docx`;
export const getTextDownloadUrl = (taskId: string) => `${API_URL}/tasks/${taskId}/output`;

export interface EquipmentEventItem {
  id: string;
  event_type: string;
  event_date?: string | null;
  created_at?: string | null;
  source_task_id?: string | null;
  event_data: Record<string, any>;
}

export interface EquipmentDetail {
  id: string;
  equipment_id: string;
  equipment_name?: string | null;
  unit?: string | null;
  equipment_type?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  events_count: number;
  events: EquipmentEventItem[];
}

export interface EquipmentSummary {
  id: string;
  equipment_id: string;
  equipment_name?: string | null;
  unit?: string | null;
  equipment_type?: string | null;
  events_count: number;
  latest_event_date?: string | null;
  latest_event_type?: string | null;
  latest_status?: string | null;
}

export interface TrendPoint {
  date: string;
  value: number;
  event_type?: string;
  projected?: boolean;
  days_from_latest?: number;
}

export interface EquipmentTrendData {
  insufficient_data: boolean;
  trending: boolean;
  equipment_id?: string;
  equipment_name?: string | null;
  unit?: string | null;
  field: string;
  current_value?: number;
  projected_value?: number;
  days_to_threshold?: number | null;
  threshold?: number;
  slope_per_day?: number;
  slope_per_month?: number;
  horizon_days?: number;
  model_type?: string;
  confidence?: string;
  r_squared?: number;
  historical_points?: TrendPoint[];
  projected_points?: TrendPoint[];
  message?: string;
}

export interface GraphQueryResult {
  query: {
    unit?: string | null;
    event_type?: string | null;
    compliance_status?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    trending_toward_violation?: boolean | null;
  };
  total_equipment_matched: number;
  results: {
    id: string;
    equipment_id: string;
    equipment_name?: string | null;
    unit?: string | null;
    equipment_type?: string | null;
    matching_events_count: number;
    events: EquipmentEventItem[];
    trend_analysis?: EquipmentTrendData | null;
  }[];
}

export const fetchAllEquipment = async (): Promise<EquipmentSummary[]> => {
  const response = await fetch(`${API_URL}/graph/equipment`);
  if (!response.ok) throw new Error("Failed to fetch equipment list");
  return response.json();
};

export const fetchEquipmentDetail = async (equipmentId: string): Promise<EquipmentDetail> => {
  const response = await fetch(`${API_URL}/graph/equipment/${encodeURIComponent(equipmentId)}`);
  if (!response.ok) throw new Error(`Failed to fetch history for equipment ${equipmentId}`);
  return response.json();
};

export const fetchEquipmentTrend = async (
  equipmentId: string,
  field: string = "vibration_rms_mms",
  horizonDays: number = 90
): Promise<EquipmentTrendData> => {
  const response = await fetch(
    `${API_URL}/graph/equipment/${encodeURIComponent(equipmentId)}/trend?field=${encodeURIComponent(field)}&horizon_days=${horizonDays}`
  );
  if (!response.ok) throw new Error(`Failed to fetch trend for equipment ${equipmentId}`);
  return response.json();
};

export const queryEquipmentGraph = async (criteria: {
  unit?: string;
  event_type?: string;
  compliance_status?: string;
  start_date?: string;
  end_date?: string;
  trending_toward_violation?: boolean;
}): Promise<GraphQueryResult> => {
  const response = await fetch(`${API_URL}/graph/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": getUserRole()
    },
    body: JSON.stringify(criteria),
  });
  if (!response.ok) throw new Error("Failed to execute equipment graph query");
  return response.json();
};
