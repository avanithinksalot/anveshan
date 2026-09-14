export interface Totals {
  works: number;
  total_sanctioned: number;
  high_works: number;
  hard_violations: number;
}

export interface DashboardSummary {
  role: string;
  scope: string;
  totals: Totals;
  tiers: { low: number; medium: number; high: number };
  top_states_by_high?: Record<string, number>;
  districts_by_risk?: Record<string, number>;
  works?: WorkRow[];
}

export interface WorkRow {
  work_id: string;
  risk_score: number;
  risk_tier: string;
  state?: string;
  ida?: string;
  mp_name?: string;
  work_category_suffix?: string;
  work_description?: string;
  sanction_amount?: number;
  disbursed_amount?: number;
  work_status?: string;
  shap_reason?: string;
  bypass_ml?: boolean;
}

export interface AlertRow {
  work_id: string;
  risk_score: number;
  risk_tier: string;
  state?: string;
  ida?: string;
  mp_name?: string;
  work_category_suffix?: string;
  work_description?: string;
  sanction_amount?: number;
  disbursed_amount?: number;
  work_status?: string;
  shap_reason?: string;
  bypass_ml?: boolean;
}

export interface AlertsResponse {
  count?: number;
  filters?: Record<string, unknown>;
  alerts: AlertRow[];
}

export interface RiskResponse {
  work_id: string;
  risk_score: number;
  risk_tier: string;
  bypass_ml: boolean;
  source_table?: string;
  state?: string;
  ida?: string;
  mp_name?: string;
  work_category_suffix?: string;
  work_description?: string;
  sanction_amount?: number;
  disbursed_amount?: number;
  work_status?: string;
  shap_reason?: string;
  components?: Record<string, number>;
}

export interface AuditAction extends AlertAuditBase {
  id?: number;
}

export interface AlertAuditBase {
  work_id: string;
  action: string;
  note?: string;
  reviewer?: string;
  risk_score_at?: number;
  risk_tier_at?: string;
  recorded_at?: string;
  work_description?: string;
  state?: string;
  ida?: string;
  mp_name?: string;
  work_category_suffix?: string;
  sanction_amount?: number;
  work_status?: string;
}

export interface AuditResponse {
  role: string;
  counts: { total: number; cleared: number; escalated: number; confirmed: number };
  actions: AuditAction[];
}