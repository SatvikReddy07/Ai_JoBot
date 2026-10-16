import {
  Job, JobListResponse, DashboardStats, EmployerBoard,
  SearchHistoryItem, Settings, UserProfile, AIJobAssessment, AIUsageStats, CVUploadResponse
} from "../types";



const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = "An unexpected error occurred.";
    try {
      const data = await res.json();
      errorDetail = data.detail || JSON.stringify(data);
    } catch {
      errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE_URL}/api/dashboard/stats`, { cache: "no-store" });
  return handleResponse<DashboardStats>(res);
}

export interface JobFilterParams {
  q?: string;
  country?: string;
  city?: string;
  company?: string;
  job_title?: string;
  min_score?: number;
  match_level?: string;
  ai_priority?: string;
  employment_type?: string;
  sponsorship_status?: string;
  application_status?: string;
  is_saved?: boolean;
  sort_by?: string;
  page?: number;
  page_size?: number;
}

export async function getJobs(params: JobFilterParams = {}): Promise<JobListResponse> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== "" && val !== "All") {
      searchParams.append(key, String(val));
    }
  });

  const res = await fetch(`${API_BASE_URL}/api/jobs?${searchParams.toString()}`, { cache: "no-store" });
  return handleResponse<JobListResponse>(res);
}

export async function getJobById(id: number): Promise<Job> {
  const res = await fetch(`${API_BASE_URL}/api/jobs/${id}`, { cache: "no-store" });
  return handleResponse<Job>(res);
}

export async function toggleSaveJob(id: number, is_saved: boolean): Promise<{ message: string; is_saved: boolean; application_status: string }> {
  const res = await fetch(`${API_BASE_URL}/api/jobs/${id}/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_saved })
  });
  return handleResponse(res);
}

export async function updateJobStatus(id: number, status: string, notes?: string): Promise<{ message: string; current_status: string }> {
  const res = await fetch(`${API_BASE_URL}/api/jobs/${id}/status`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, notes })
  });
  return handleResponse(res);
}

export async function runSearchNow(board_id?: number): Promise<{ status: string; boards_searched: number; jobs_found: number; jobs_new: number; jobs_updated: number; message: string }> {
  const url = board_id ? `${API_BASE_URL}/api/search/run?board_id=${board_id}` : `${API_BASE_URL}/api/search/run`;
  const res = await fetch(url, { method: "POST" });
  return handleResponse(res);
}

export async function getSearchHistory(): Promise<SearchHistoryItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/search/history`, { cache: "no-store" });
  return handleResponse<SearchHistoryItem[]>(res);
}

export async function getSettings(): Promise<Settings> {
  const res = await fetch(`${API_BASE_URL}/api/settings`, { cache: "no-store" });
  return handleResponse<Settings>(res);
}

export async function updateSettings(settings: Partial<Settings>): Promise<Settings> {
  const res = await fetch(`${API_BASE_URL}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings)
  });
  return handleResponse<Settings>(res);
}

export async function getEmployers(): Promise<EmployerBoard[]> {
  const res = await fetch(`${API_BASE_URL}/api/employers`, { cache: "no-store" });
  return handleResponse<EmployerBoard[]>(res);
}

export async function addEmployer(employer: { company_name: string; platform: string; board_token: string; is_enabled: boolean }): Promise<EmployerBoard> {
  const res = await fetch(`${API_BASE_URL}/api/employers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(employer)
  });
  return handleResponse<EmployerBoard>(res);
}

export async function updateEmployer(id: number, employer: Partial<EmployerBoard>): Promise<EmployerBoard> {
  const res = await fetch(`${API_BASE_URL}/api/employers/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(employer)
  });
  return handleResponse<EmployerBoard>(res);
}

export async function deleteEmployer(id: number): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/employers/${id}`, { method: "DELETE" });
  return handleResponse(res);
}

export function getExportCsvUrl(params: JobFilterParams = {}): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== "" && val !== "All") {
      searchParams.append(key, String(val));
    }
  });
  return `${API_BASE_URL}/api/jobs/export?${searchParams.toString()}`;
}

// -------------------------------------------------------------
// Phase 2: Career Profile & Gemini AI Integration
// -------------------------------------------------------------

export async function getUserProfile(): Promise<UserProfile> {

  const res = await fetch(`${API_BASE_URL}/api/profile`, { cache: "no-store" });
  return handleResponse<UserProfile>(res);
}

export async function updateUserProfile(profile: Partial<UserProfile>): Promise<UserProfile> {
  const res = await fetch(`${API_BASE_URL}/api/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile)
  });
  return handleResponse<UserProfile>(res);
}

export async function uploadMasterCv(file: File): Promise<CVUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE_URL}/api/profile/upload-cv`, {
    method: "POST",
    body: formData
  });
  return handleResponse<CVUploadResponse>(res);
}


export async function setUserAiConsent(consent_given: boolean): Promise<{ message: string; consent_given_for_ai: boolean }> {
  const res = await fetch(`${API_BASE_URL}/api/profile/consent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ consent_given })
  });
  return handleResponse(res);
}

export function getCvDownloadUrl(): string {
  return `${API_BASE_URL}/api/profile/cv/download`;
}

export async function analyzeJobWithAi(jobId: number, force_reanalyze: boolean = false): Promise<AIJobAssessment> {
  const res = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/ai-analyze?force_reanalyze=${force_reanalyze}`, {
    method: "POST"
  });
  return handleResponse<AIJobAssessment>(res);
}

export async function getJobAiAssessment(jobId: number): Promise<AIJobAssessment | null> {
  const res = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/ai-assessment`, { cache: "no-store" });
  if (res.status === 404) return null;
  return handleResponse<AIJobAssessment>(res);
}

export async function getAiUsageStats(): Promise<AIUsageStats> {
  const res = await fetch(`${API_BASE_URL}/api/ai/usage`, { cache: "no-store" });
  return handleResponse<AIUsageStats>(res);
}

