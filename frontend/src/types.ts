export type Role = "secretary" | "coordinator" | "instructor" | "communication";
export type User = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  access_status: "pending" | "approved" | "rejected";
  roles: Role[];
};
export type RecordData = { id: number; [key: string]: unknown };
export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
export type Eligibility = {
  eligible: boolean | null;
  status: string;
  reason: string;
  decisions: string[];
};
export type Student = RecordData & {
  name: string;
  cpf: string;
  email: string;
  phone: string;
  birth_date: string | null;
  address: string;
  notes: string;
  archived: boolean;
};
export type Enrollment = RecordData & {
  student: number;
  student_name: string;
  class_group: number;
  class_name: string;
  start_date: string;
  plan: string;
  amount: string;
  administrative_status: string;
  kind: string;
  eligibility: Eligibility;
};
export type Policy = { id: string; title: string; impact: string };
export type Policies = {
  pending: Policy[];
  approved: string[];
  demo: boolean;
  timezone: string;
};
export type Summary = {
  students: number;
  enrollments: number;
  leads: number;
  conversions: number;
  classes: number;
  pending_users: number;
  received: string;
  expected: string;
  outstanding: string;
  overdue: string;
  financial_definition: string;
  pending_decisions: string[];
  categories: unknown;
  [key: string]: unknown;
};
