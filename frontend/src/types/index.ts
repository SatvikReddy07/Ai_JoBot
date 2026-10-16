export interface Job {
  id: number;
  source: string;
  source_job_id: string;
  company: string;
  title: string;
  normalized_title?: string;
  location: string;
  city?: string;
  country?: string;
  employment_type: string;
  is_permanent_fulltime: boolean;
  description: string;
  raw_description_html?: string;
  url: string;
  posted_date?: string;
  discovered_at: string;
  last_verified_at: string;
  is_active: boolean;
  match_score: number;
  match_level: "Excellent Match" | "Strong Match" | "Potential Match" | "Low Match";
  match_reasons: string[];
  matching_qualifications: string[];
  matching_experience: string[];
  matching_skills: string[];
  missing_requirements: string[];
  location_suitability?: string;
  sponsorship_status: "Confirmed" | "Not Supported" | "Unknown";
  application_status: "Discovered" | "Saved" | "Interested" | "Ready to Apply" | "Applied" | "Interview" | "Offer" | "Rejected" | "Closed";
  application_notes?: string;
  is_saved: boolean;
  ai_assessment?: AIJobAssessment;
}

export interface MasterCV {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  extracted_at: string;
  is_active: boolean;
}

export interface EmploymentRecord {
  company: string;
  role: string;
  location?: string;
  duration?: string;
  highlights: string[];
  source?: string;
}

export interface UserProfile {
  id: number;
  name: string;
  current_role: string;
  current_company: string;
  location: string;
  experience_years: number;
  summary: string;
  employment_history: EmploymentRecord[];
  qualifications: string[];
  skills: string[];
  achievements: string[];
  target_countries: string[];
  target_titles: string[];
  consent_given_for_ai: boolean;
  last_updated_at: string;
  cv?: MasterCV;
}

export interface CVUploadResponse {
  message: string;
  cv_id: number;
  filename: string;
  profile: UserProfile;
}

export interface AIJobAssessment {

  id: number;
  job_id: number;
  job_hash: string;
  match_score: number;
  application_priority: "High" | "Medium" | "Low";
  career_growth_score: number;
  career_growth_summary: string;
  matching_skills: string[];
  missing_requirements: string[];
  qualification_alignment: string[];
  experience_alignment: string[];
  industry_alignment: string[];
  visa_relocation_considerations: string;
  reasons_to_apply: string[];
  reasons_to_reconsider: string[];
  evidence_references: Record<string, any>;
  model_used: string;
  engine_used: "ai" | "rules_fallback";
  created_at: string;
}

export interface AIUsageStats {
  daily_used: number;
  daily_limit: number;
  remaining: number;
  is_active: boolean;
  model_name: string;
  free_tier_status: string;
}

export interface JobListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: Job[];
}

export interface DashboardStats {
  total_jobs: number;
  new_jobs_today: number;
  excellent_matches: number;
  strong_matches: number;
  saved_opportunities: number;
  active_applications: number;
  last_successful_search?: string;
}

export interface EmployerBoard {
  id: number;
  company_name: string;
  platform: "greenhouse" | "lever";
  board_token: string;
  is_enabled: boolean;
  created_at: string;
  last_searched_at?: string;
  last_status?: string;
  last_job_count: number;
}

export interface SearchHistoryItem {
  id: number;
  started_at: string;
  completed_at?: string;
  status: string;
  jobs_found: number;
  jobs_new: number;
  jobs_updated: number;
  boards_searched: number;
  error_message?: string;
}

export interface ScoringWeights {
  experience_seniority: number;
  hse_technical_skills: number;
  qualifications: number;
  industry_relevance: number;
  location_international: number;
  employment_preferences: number;
}

export interface Settings {
  profile_name: string;
  profile_current_role: string;
  profile_experience_years: number;
  target_countries: string[];
  target_titles: string[];
  min_match_score: number;
  scoring_weights: ScoringWeights;
  auto_search_hour: number;
  auto_search_minute: number;
  updated_at: string;
}

