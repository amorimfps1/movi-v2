import { useState, useEffect } from "react";
import {
  Routes,
  Route,
  Navigate,
  NavLink,
  Outlet,
  Link,
  useLocation,
} from "react-router-dom";
import {
  LayoutDashboard,
  UsersRound,
  ContactRound,
  Shapes,
  CalendarDays,
  GraduationCap,
  Wallet,
  ChartNoAxesCombined,
  ShieldCheck,
  History,
  BookOpen,
  LogOut,
  Menu,
  X,
  ArrowUpRight,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuth, isAdmin, Login } from "./auth";
import { Loading, Button, ErrorNotice, Notice, PageTitle } from "./ui";
import { roleNames } from "./format";
import { ThemeProvider, ThemeToggle } from "./theme";
import { EcoWork, personSpec, condominiumSpec, associationSpec, residenceSpec } from "./EcoWork";
import { ResourceList, StudentDetail } from "./resources";
import {
  studentSpec,
  enrollmentSpec,
  leadSpec,
  modalitySpec,
  instructorSpec,
} from "./schema";
import { Dashboard } from "./Dashboard";
import { EnrollmentDetail } from "./EnrollmentDetail";
import { useApi } from "./query";
import type { Policies } from "./types";
import { RecordDetail } from "./RecordDetail";
import { AcademicList, ClassDetail, LessonDetail } from "./Academic";
import { Finance, ChargeDetail, PaymentDetail } from "./Finance";
import { Reports, PoliciesPage } from "./Reports";
import { AccessList, AccessDetail, AuditList, AuditDetail } from "./Management";
import { FinancialCatalog } from "./FinancialCatalog";
import { LeadRetention } from "./LeadRetention";
type NavItem = {
  path: string;
  label: string;
  icon: LucideIcon;
  admin?: boolean;
  coordinator?: boolean;
  commercial?: boolean;
  academic?: boolean;
};
const groups: { label: string; items: NavItem[] }[] = [
  {
    label: "ACOMPANHAMENTO",
    items: [
      { path: "/", label: "Visão geral", icon: LayoutDashboard },
      { path: "/alunos", label: "Alunos", icon: UsersRound, admin: true },
      {
        path: "/interessados",
        label: "Leads",
        icon: ContactRound,
        commercial: true,
      },
      {
        path: "/matriculas",
        label: "Matrículas",
        icon: GraduationCap,
        admin: true,
      },
    ],
  },
  {
    label: "ATIVIDADES",
    items: [
      { path: "/turmas", label: "Turmas", icon: BookOpen, academic: true },
      {
        path: "/aulas",
        label: "Aulas e chamada",
        icon: CalendarDays,
        academic: true,
      },
      { path: "/modalidades", label: "Modalidades", icon: Shapes, admin: true },
      {
        path: "/instrutores",
        label: "Instrutores",
        icon: ContactRound,
        admin: true,
      },
    ],
  },
  {
    label: "GESTÃO",
    items: [
      { path: "/financeiro", label: "Financeiro", icon: Wallet, admin: true },
      { path: "/ecowork", label: "EcoWork", icon: Wallet, admin: true },
      { path: "/pessoas", label: "Pessoas", icon: UsersRound, admin: true },
      { path: "/revisao-contatos", label: "Revisão de contatos", icon: History, admin: true },
      { path: "/relatorios", label: "Relatórios", icon: ChartNoAxesCombined },
      {
        path: "/acessos",
        label: "Contas e perfis",
        icon: ShieldCheck,
        coordinator: true,
      },
      { path: "/configuracoes-financeiras", label: "Tabelas financeiras", icon: Wallet, coordinator: true },
      { path: "/auditoria", label: "Histórico", icon: History, admin: true },
    ],
  },
];
function Shell() {
  const { user, loading, logout } = useAuth();
  const [navOpen, setNavOpen] = useState(false);
  const [error, setError] = useState<unknown>();
  const [leaving, setLeaving] = useState(false);
  const policies = useApi<Policies>(
    "policies/",
    user?.access_status === "approved" && !!user.roles.length,
  );
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.access_status !== "approved" || !user.roles.length)
    return (
      <div className="access-state">
        <ThemeToggle />
        <Link className="wordmark" to="/login">
          movi<span>+</span>
        </Link>
        <Notice tone="warning">
          Sua conta está{" "}
          {user.access_status === "rejected"
            ? "rejeitada"
            : "pendente de aprovação"}
          . A equipe responsável precisa revisar a solicitação.
        </Notice>
        <Button onClick={() => void logout()}>Voltar ao acesso</Button>
      </div>
    );
  const admin = isAdmin(user);
  const instructor = user.roles.includes("instructor");
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Ir para o conteúdo
      </a>
      <header className="mobile-bar">
        <Link to="/" className="wordmark">
          movi<span>+</span>
        </Link>
        <div className="mobile-bar-actions">
          <ThemeToggle compact />
          <Button
            variant="ghost"
            aria-label={navOpen ? "Fechar navegação" : "Abrir navegação"}
            aria-expanded={navOpen}
            onClick={() => setNavOpen(!navOpen)}
          >
            {navOpen ? <X /> : <Menu />}
          </Button>
        </div>
      </header>
      {navOpen && (
        <button
          className="nav-overlay"
          aria-label="Fechar navegação"
          onClick={() => setNavOpen(false)}
        />
      )}
      <aside className={`sidebar ${navOpen ? "sidebar--open" : ""}`}>
        <Link to="/" className="wordmark" onClick={() => setNavOpen(false)}>
          movi<span>+</span>
        </Link>
        <span className="workspace-label">ALUNOS · MATRÍCULAS · LEADS</span>
        <nav aria-label="Navegação principal">
          {groups.map((group) => {
            const visible = group.items
              .filter((item) => !item.admin || admin)
              .filter((item) => !item.coordinator || user.roles.includes("coordinator"))
              .filter((item) => !item.commercial || admin || user.roles.includes("communication"))
              .filter((item) => !item.academic || admin || instructor)
              .filter(
                (item) =>
                  item.path !== "/relatorios" ||
                  admin ||
                  user.roles.includes("communication"),
              );
            return (
              visible.length > 0 && (
                <div className="nav-group" key={group.label}>
                  <p>{group.label}</p>
                  {visible.map((item) => (
                    <NavLink
                      end={item.path === "/"}
                      to={item.path}
                      key={item.path}
                      onClick={() => setNavOpen(false)}
                      className={({ isActive }) =>
                        isActive ? "nav-link nav-link--active" : "nav-link"
                      }
                    >
                      <item.icon size={19} />
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              )
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <ThemeToggle />
          <Link className="help-link" to="/politicas">
            Regras e decisões <ArrowUpRight size={15} />
          </Link>
          <div className="user-profile">
            <span className="avatar">
              {(user.first_name || user.email)[0].toUpperCase()}
            </span>
            <div>
              <strong>{user.first_name || user.email}</strong>
              <small>
                {user.roles.map((role) => roleNames[role]).join(" · ")}
              </small>
            </div>
            <Button
              variant="ghost"
              aria-label="Sair do MOVI+"
              disabled={leaving}
              onClick={async () => {
                setLeaving(true);
                try {
                  await logout();
                } catch (err) {
                  setError(err);
                } finally {
                  setLeaving(false);
                }
              }}
            >
              <LogOut size={18} />
            </Button>
          </div>
        </div>
      </aside>
      <main id="main-content" className="main-content" tabIndex={-1}>
        <ErrorNotice error={error} />
        {policies.data?.demo && (
          <div className="demo-banner" role="status">
            <strong>DEMONSTRAÇÃO</strong>
            <span>Registros de exemplo em ambiente isolado.</span>
            <Link to="/politicas">Ver regras</Link>
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
function AdminGuard() {
  const { user } = useAuth();
  return isAdmin(user) ? <Outlet /> : <Unauthorized />;
}
function CoordinatorGuard() {
  const { user } = useAuth();
  return user?.roles.includes("coordinator") ? <Outlet /> : <Unauthorized />;
}
function CommercialGuard() {
  const { user } = useAuth();
  return isAdmin(user) || user?.roles.includes("communication") ? <Outlet /> : <Unauthorized />;
}
function CommercialLeads({ detail = false }: { detail?: boolean }) {
  const { user } = useAuth();
  const spec = isAdmin(user) ? leadSpec : { ...leadSpec, readOnly: true, filterFields: [],
    fields: [...leadSpec.fields.filter((field) => ['name', 'email', 'phone', 'source', 'status'].includes(field.key)), { key: 'whatsapp', label: 'WhatsApp autorizado' }],
    columns: [{ key: 'name', label: 'Lead' }, { key: 'email', label: 'E-mail autorizado' }, { key: 'phone', label: 'Telefone autorizado' }, { key: 'whatsapp', label: 'WhatsApp autorizado' }, { key: 'status', label: 'Situação' }] };
  return detail ? <RecordDetail spec={spec} /> : <ResourceList spec={spec} />;
}
function AcademicGuard() {
  const { user } = useAuth();
  return isAdmin(user) || user?.roles.includes("instructor") ? (
    <Outlet />
  ) : (
    <Unauthorized />
  );
}
function Unauthorized() {
  return (
    <>
      <PageTitle
        title="Acesso restrito"
        description="Seu perfil não tem permissão para esta rotina."
      />
      <Link className="button button--secondary" to="/">
        Voltar para a visão geral
      </Link>
    </>
  );
}
function NotFound() {
  return (
    <>
      <PageTitle
        title="Página não encontrada"
        description="O endereço informado não corresponde a uma rotina do MOVI+."
      />
      <Link className="button button--secondary" to="/">
        Voltar para a visão geral
      </Link>
    </>
  );
}
export function App() {
  const { pathname } = useLocation();
  useEffect(() => {
    const root = document.documentElement;
    const pointer = () => {
      root.dataset.inputMethod = "pointer";
    };
    const keyboard = (event: KeyboardEvent) => {
      if (
        event.key === "Tab" ||
        [
          "ArrowUp",
          "ArrowDown",
          "ArrowLeft",
          "ArrowRight",
          "Home",
          "End",
          "PageUp",
          "PageDown",
        ].includes(event.key)
      ) {
        root.dataset.inputMethod = "keyboard";
      }
    };
    window.addEventListener("pointerdown", pointer, true);
    window.addEventListener("keydown", keyboard, true);
    return () => {
      window.removeEventListener("pointerdown", pointer, true);
      window.removeEventListener("keydown", keyboard, true);
      delete root.dataset.inputMethod;
    };
  }, []);
  useEffect(() => {
    window.scrollTo(0, 0);
    document.getElementById("main-content")?.focus({ preventScroll: true });
  }, [pathname]);
  return (
    <ThemeProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/solicitar-acesso" element={<Login register />} />
        <Route element={<Shell />}>
          <Route index element={<Dashboard />} />
          <Route element={<AdminGuard />}>
            <Route path="ecowork" element={<EcoWork />} />
            <Route path="revisao-contatos" element={<LeadRetention />} />
            {[personSpec, condominiumSpec, associationSpec, residenceSpec].map(spec => <Route key={spec.slug} path={spec.slug}>
              <Route index element={<ResourceList key={spec.slug} spec={spec} />} />
              <Route path=":id" element={<RecordDetail key={spec.slug} spec={spec} />} />
            </Route>)}
            <Route
              path="alunos"
              element={<ResourceList key="students" spec={{ ...studentSpec, readOnly: true, description: 'Pessoas com matrícula acadêmica, incluindo o histórico de matrículas encerradas.', fixedParams: { has_enrollments: 'true' } }} beforeList={<Link className="back-link" to="/pessoas">Cadastrar ou consultar uma pessoa sem matrícula</Link>} />}
            />
            <Route path="alunos/:id" element={<StudentDetail />} />
            <Route
              path="matriculas"
              element={<ResourceList key="enrollments" spec={enrollmentSpec} />}
            />
            <Route path="matriculas/:id" element={<EnrollmentDetail />} />
            {[modalitySpec, instructorSpec].map((spec) => (
              <Route key={spec.slug} path={spec.slug}>
                <Route
                  index
                  element={<ResourceList key={spec.slug} spec={spec} />}
                />
                <Route
                  path=":id"
                  element={<RecordDetail key={spec.slug} spec={spec} />}
                />
              </Route>
            ))}
            <Route path="financeiro" element={<Finance />} />
            <Route
              path="cobrancas"
              element={<Navigate to="/financeiro" replace />}
            />
            <Route path="cobrancas/:id" element={<ChargeDetail />} />
            <Route path="recebimentos" element={<Finance payments />} />
            <Route path="recebimentos/:id" element={<PaymentDetail />} />
            <Route element={<CoordinatorGuard />}>
              <Route path="acessos" element={<AccessList />} />
              <Route path="acessos/:id" element={<AccessDetail />} />
              <Route path="configuracoes-financeiras" element={<FinancialCatalog />} />
            </Route>
            <Route path="auditoria" element={<AuditList />} />
            <Route path="auditoria/:id" element={<AuditDetail />} />
          </Route>
          <Route element={<CommercialGuard />}>
            <Route path="interessados" element={<CommercialLeads />} />
            <Route path="interessados/:id" element={<CommercialLeads detail />} />
          </Route>
          <Route element={<AcademicGuard />}>
            <Route path="turmas" element={<AcademicList classes />} />
            <Route path="turmas/:id" element={<ClassDetail />} />
            <Route path="aulas" element={<AcademicList />} />
            <Route path="aulas/:id" element={<LessonDetail />} />
          </Route>
          <Route path="relatorios" element={<Reports />} />
          <Route path="politicas" element={<PoliciesPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </ThemeProvider>
  );
}
