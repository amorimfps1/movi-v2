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
  ChevronDown,
  LogOut,
  Menu,
  X,
  ArrowUpRight,
} from "lucide-react";
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
import { EcoCatalog } from "./EcoCatalog";
import { payoutAgreementSpec, PayoutAgreementDetail } from "./PayoutAgreements";
import { LeadRetention } from "./LeadRetention";
import { benefitSpec, BenefitDetail } from "./Benefits";
type NavItem = {
  path: string;
  label: string;
  admin?: boolean;
  coordinator?: boolean;
  commercial?: boolean;
  academic?: boolean;
};
const groups: { label: string; items: NavItem[] }[] = [
  {
    label: "INDICADORES",
    items: [
      { path: "/", label: "Visão geral" },
      { path: "/relatorios", label: "Relatórios" },
    ],
  },
  {
    label: "PESSOAS E MATRÍCULAS",
    items: [
      { path: "/alunos", label: "Alunos", admin: true },
      {
        path: "/interessados",
        label: "Leads",
        commercial: true,
      },
      { path: "/pessoas", label: "Pessoas", admin: true },
      {
        path: "/matriculas",
        label: "Matrículas",
        admin: true,
      },
      { path: "/revisao-contatos", label: "Revisão de contatos", admin: true },
    ],
  },
  {
    label: "ATIVIDADES",
    items: [
      { path: "/turmas", label: "Turmas", academic: true },
      {
        path: "/aulas",
        label: "Aulas e chamada",
        academic: true,
      },
      { path: "/modalidades", label: "Modalidades", admin: true },
      {
        path: "/instrutores",
        label: "Instrutores",
        admin: true,
      },
    ],
  },
  {
    label: "FINANCEIRO",
    items: [
      { path: "/financeiro", label: "Financeiro", admin: true },
      { path: "/beneficios", label: "Bolsas e descontos", admin: true },
      { path: "/configuracoes-financeiras", label: "Tabelas financeiras", coordinator: true },
      { path: "/acordos-repasse", label: "Acordos de repasse", coordinator: true },
    ],
  },
  {
    label: "ECOWORK",
    items: [
      { path: "/ecowork", label: "EcoWork", admin: true },
      { path: "/catalogo-ecowork", label: "Catálogo EcoWork", coordinator: true },
    ],
  },
  {
    label: "ADMINISTRAÇÃO",
    items: [
      {
        path: "/acessos",
        label: "Contas e perfis",
        coordinator: true,
      },
      { path: "/auditoria", label: "Histórico", admin: true },
    ],
  },
];
function groupForPath(pathname: string) {
  if (/^\/(cobrancas|recebimentos)(\/|$)/.test(pathname)) return "FINANCEIRO";
  return groups.find((group) => group.items.some((item) =>
    item.path === "/" ? pathname === "/" : pathname === item.path || pathname.startsWith(`${item.path}/`),
  ))?.label;
}
function Shell() {
  const { user, loading, logout } = useAuth();
  const { pathname } = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const [openGroups, setOpenGroups] = useState<string[]>(() => {
    const active = groupForPath(pathname);
    return active ? [active] : [];
  });
  const [error, setError] = useState<unknown>();
  const [leaving, setLeaving] = useState(false);
  const policies = useApi<Policies>(
    "policies/",
    user?.access_status === "approved" && !!user.roles.length,
  );
  useEffect(() => {
    const active = groupForPath(pathname);
    if (active) setOpenGroups((open) => open.includes(active) ? open : [...open, active]);
  }, [pathname]);
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
          {groups.map((group, index) => {
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
                  <button
                    type="button"
                    className="nav-group__toggle"
                    aria-expanded={openGroups.includes(group.label)}
                    aria-controls={`nav-group-${index}`}
                    onClick={() => setOpenGroups((open) => open.includes(group.label)
                      ? open.filter((label) => label !== group.label)
                      : [...open, group.label])}
                  >
                    {group.label}
                    <ChevronDown size={16} aria-hidden="true" />
                  </button>
                  <div id={`nav-group-${index}`} className="nav-group__items" aria-hidden={!openGroups.includes(group.label)} inert={!openGroups.includes(group.label)}>
                  <div className="nav-group__items-inner">
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
                      {item.label}
                    </NavLink>
                  ))}
                  </div>
                  </div>
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
    columns: [{ key: 'name', label: 'Lead' }, { key: 'email', label: 'E-mail autorizado' }, { key: 'phone', label: 'Telefone autorizado' }, { key: 'whatsapp', label: 'WhatsApp autorizado' }, ...leadSpec.columns.filter((column) => column.key === 'trial_status'), { key: 'status', label: 'Situação' }] };
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
            <Route path="beneficios" element={<ResourceList spec={benefitSpec} />} />
            <Route path="beneficios/:id" element={<BenefitDetail />} />
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
              <Route path="catalogo-ecowork" element={<EcoCatalog />} />
              <Route path="acordos-repasse" element={<ResourceList spec={payoutAgreementSpec} />} />
              <Route path="acordos-repasse/:id" element={<PayoutAgreementDetail />} />
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
