export type Role = 'staff' | 'supervisor' | 'hr';
export type Category = 'Critical' | 'Moderate' | 'Minor';

export interface LoginResponse { access_token: string; token_type: string; role: Role; name: string; user_id: number; }
export interface Session { token: string; role: Role; name: string; user_id: number; }
export interface Cycle { id: number; year: number; is_open: boolean; }

export interface SurveyQuestion { id: number; competency: string; text: string; answer: number | null; }
export interface SurveyView { cycle: Cycle; answered: number; total: number; questions: SurveyQuestion[]; }

export interface TeamMember { staff_id: number; name: string; rated: number; total: number; status: string; }
export interface TeamView { cycle: Cycle; team: TeamMember[]; }
export interface RatingQuestion { question_id: number; competency: string; required: number | null; text: string; rating: number | null; }
export interface RatingView { staff: { id: number; name: string }; cycle: Cycle; questions: RatingQuestion[]; }

export interface Person { id: number; name: string; role: Role; job_scope: string | null; department: string | null; }
export interface NamedItem { id: number; name: string; }

export interface ReportRow {
  competency_id: number; competency: string; required: number; self: number;
  supervisor: number | null; actual: number; gap: number; category: Category;
  supervisor_pending: boolean;
}
export interface IndividualReport {
  header: {
    staff_name: string; job_scope: string; department: string | null; cycle: Cycle;
    supervisor_rating_status: string; survey_progress: string;
  };
  rows: ReportRow[];
  summary: string;
}
export interface DeptStaff { id: number; name: string; actual: number; gap: number; category: Category; }
export interface DeptRow {
  competency: string; required: number; avg_actual: number; avg_gap: number;
  critical: number; moderate: number; minor: number; staff_count: number;
  staff: DeptStaff[];
}
export interface DeptReport {
  header: {
    department: string; cycle: Cycle; staff_assessed: number; staff_total: number;
    supervisor_ratings_incomplete: number;
  };
  competencies: DeptRow[];
  top_priorities: (DeptRow & { rank: number })[];
}

export interface SetupQuestion {
  id: number; competency_id: number; competency: string; text: string;
  is_negative: boolean; answer_count: number;
}
export interface SetupScope {
  id: number; name: string;
  competencies: { competency_id: number; name: string; required_level: number }[];
  questions: SetupQuestion[];
}
export interface SetupOverview { job_scopes: SetupScope[]; competencies: NamedItem[]; departments: NamedItem[]; }
