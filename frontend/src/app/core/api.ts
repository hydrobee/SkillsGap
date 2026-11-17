import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { API_URL } from './config';
import {
  Cycle, DeptReport, IndividualReport, LoginResponse, NamedItem, Person, RatingView,
  SetupOverview, SurveyView, TeamView,
} from './models';

@Injectable({ providedIn: 'root' })
export class Api {
  private http = inject(HttpClient);
  private u = (path: string) => API_URL + path;
  private cyc = (id?: number | null) => (id ? { params: new HttpParams().set('cycle_id', id) } : {});

  // auth
  login(email: string, password: string) {
    const body = new HttpParams().set('username', email).set('password', password);
    return this.http.post<LoginResponse>(this.u('/auth/login'), body);
  }

  // survey
  survey() { return this.http.get<SurveyView>(this.u('/survey/me')); }
  saveSurvey(cycleId: number, answers: { question_id: number; answer: number }[]) {
    return this.http.put(this.u('/survey/me'), { cycle_id: cycleId, answers });
  }

  // supervisor rating
  team() { return this.http.get<TeamView>(this.u('/rating/team')); }
  ratings(staffId: number) { return this.http.get<RatingView>(this.u(`/rating/${staffId}`)); }
  saveRatings(staffId: number, cycleId: number, ratings: { question_id: number; rating: number }[]) {
    return this.http.put(this.u(`/rating/${staffId}`), { cycle_id: cycleId, ratings });
  }

  // reports
  cycles() { return this.http.get<Cycle[]>(this.u('/reports/cycles')); }
  people() { return this.http.get<Person[]>(this.u('/reports/people')); }
  individual(userId: number, cycleId?: number | null) {
    return this.http.get<IndividualReport>(this.u(`/reports/individual/${userId}`), this.cyc(cycleId));
  }
  departments() { return this.http.get<NamedItem[]>(this.u('/reports/departments')); }
  department(id: number, cycleId?: number | null) {
    return this.http.get<DeptReport>(this.u(`/reports/department/${id}`), this.cyc(cycleId));
  }

  // HR setup
  overview() { return this.http.get<SetupOverview>(this.u('/setup/overview')); }
  createScope(name: string) { return this.http.post(this.u('/setup/job-scopes'), { name }); }
  createCompetency(name: string) { return this.http.post(this.u('/setup/competencies'), { name }); }
  setLevel(scopeId: number, compId: number, level: number) {
    return this.http.put(this.u(`/setup/job-scopes/${scopeId}/competencies/${compId}`), { required_level: level });
  }
  removeLevel(scopeId: number, compId: number) {
    return this.http.delete(this.u(`/setup/job-scopes/${scopeId}/competencies/${compId}`));
  }
  createQuestion(q: { job_scope_id: number; competency_id: number; text: string; is_negative: boolean }) {
    return this.http.post(this.u('/setup/questions'), q);
  }
  updateQuestion(id: number, body: { text?: string; is_negative?: boolean }) {
    return this.http.put(this.u(`/setup/questions/${id}`), body);
  }
  deleteQuestion(id: number, force = false) {
    return this.http.delete(this.u(`/setup/questions/${id}`), force ? { params: new HttpParams().set('force', true) } : {});
  }
  listCycles() { return this.http.get<Cycle[]>(this.u('/setup/cycles')); }
  createCycle(year: number) { return this.http.post(this.u('/setup/cycles'), { year }); }
  closeCycle(id: number) { return this.http.post(this.u(`/setup/cycles/${id}/close`), {}); }
  openCycle(id: number) { return this.http.post(this.u(`/setup/cycles/${id}/open`), {}); }
}
