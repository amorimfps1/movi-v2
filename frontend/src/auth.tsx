import {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  useCallback,
} from "react";
import type { ReactNode, FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, ArrowRight, MoveUpRight } from "lucide-react";
import type { User } from "./types";
import { api, post, ApiError } from "./api";
import { Button, Field, ErrorNotice, Notice, Loading } from "./ui";
import { useNavigate, Link } from "react-router-dom";
const AuthContext = createContext<{
  user: User | null;
  loading: boolean;
  refresh: () => Promise<User | null>;
  logout: () => Promise<void>;
}>({
  user: null,
  loading: true,
  refresh: async () => null,
  logout: async () => {},
});
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>();
  const client = useQueryClient();
  const currentUser = useRef<User | null>(null);
  const activeRequest = useRef<Promise<User | null> | null>(null);
  const refresh = useCallback(async (): Promise<User | null> => {
    if (activeRequest.current) return activeRequest.current;
    const request = (async () => {
      try {
        const value = await api<User>("auth/me/");
        const old = currentUser.current;
        if (
          old &&
          (old.id !== value.id ||
            old.access_status !== value.access_status ||
            JSON.stringify([...old.roles].sort()) !==
              JSON.stringify([...value.roles].sort()))
        )
          client.clear();
        currentUser.current = value;
        setUser(value);
        setError(undefined);
        return value;
      } catch (err) {
        if (err instanceof ApiError && [401, 403].includes(err.status)) {
          currentUser.current = null;
          setUser(null);
          client.clear();
          setError(undefined);
          return null;
        }
        setError(err);
        return null;
      } finally {
        setLoading(false);
      }
    })();
    activeRequest.current = request;
    try {
      return await request;
    } finally {
      activeRequest.current = null;
    }
  }, [client]);
  useEffect(() => {
    void refresh();
    const expire = () => {
      currentUser.current = null;
      setUser(null);
      client.clear();
    };
    const revalidate = () => {
      void refresh();
    };
    window.addEventListener("movi:session-expired", expire);
    window.addEventListener("movi:authorization-check", revalidate);
    window.addEventListener("focus", revalidate);
    return () => {
      window.removeEventListener("movi:session-expired", expire);
      window.removeEventListener("movi:authorization-check", revalidate);
      window.removeEventListener("focus", revalidate);
    };
  }, [client, refresh]);
  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        refresh,
        logout: async () => {
          await post("auth/logout/", {});
          currentUser.current = null;
          setUser(null);
          client.clear();
        },
      }}
    >
      {error ? (
        <div className="connection-error">
          <ErrorNotice error={error} />
          <Button onClick={() => void refresh()}>
            Tentar conexão novamente
          </Button>
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
}
export const useAuth = () => useContext(AuthContext);
export const isAdmin = (user: User | null) =>
  !!user?.roles.some((role) => ["secretary", "coordinator"].includes(role));
export function Login({ register = false }: { register?: boolean }) {
  const { user, loading, refresh } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  const [registered, setRegistered] = useState(false);
  useEffect(() => {
    if (user?.access_status === "approved" && user.roles.length)
      navigate("/", { replace: true });
  }, [user, navigate]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    setPending(true);
    const fields = Object.fromEntries(new FormData(event.currentTarget));
    try {
      if (register) {
        await post("auth/register/", fields);
        setRegistered(true);
      } else {
        await post<User>("auth/login/", fields);
        await refresh();
        navigate("/");
      }
    } catch (err) {
      setError(err);
    } finally {
      setPending(false);
    }
  }
  if (loading) return <Loading />;
  return (
    <div className="auth-page">
      <aside className="auth-story">
        <Link to="/login" className="wordmark">
          movi<span>+</span>
        </Link>
        <div>
          <p className="eyebrow">GESTÃO EM MOVIMENTO</p>
          <h1>
            Alunos, matrículas
            <br />e leads no mesmo lugar.
          </h1>
          <p>
            Organize os cadastros dos alunos, acompanhe os leads e mantenha as
            matrículas conectadas à sua rotina.
          </p>
          <div className="auth-trail">
            <span>Lead</span>
            <ArrowUpRight />
            <span>Aluno</span>
            <ArrowUpRight />
            <span>Matrícula</span>
          </div>
        </div>
        <div className="auth-note">
          <MoveUpRight size={36} />
          <p>
            Do primeiro contato
            <br />
            <strong>à matrícula do aluno.</strong>
          </p>
        </div>
      </aside>
      <main className="auth-form">
        <div className="auth-mobile-brand wordmark">
          movi<span>+</span>
        </div>
        <div className="auth-form__inner">
          <p className="eyebrow">SECRETARIA · COORDENAÇÃO · INSTRUTORES</p>
          <h2>{register ? "Vamos começar." : "Bom ter você aqui."}</h2>
          <p>
            {register
              ? "Solicite seu acesso à equipe MOVI+."
              : "Entre para acompanhar as atividades de hoje."}
          </p>
          {registered ? (
            <>
              <Notice tone="success">
                <strong>Solicitação enviada.</strong>
                <br />
                Sua conta está pendente. A equipe responsável precisa aprovar o
                acesso e atribuir uma função.
              </Notice>
              <Link className="button button--primary" to="/login">
                Voltar para o acesso <ArrowRight size={18} />
              </Link>
            </>
          ) : (
            <form onSubmit={submit} className="auth-fields">
              {register && (
                <>
                  <Field label="Nome">
                    <input
                      name="first_name"
                      autoComplete="given-name"
                      required
                      maxLength={150}
                    />
                  </Field>
                  <Field label="Sobrenome">
                    <input
                      name="last_name"
                      autoComplete="family-name"
                      required
                      maxLength={150}
                    />
                  </Field>
                </>
              )}
              <Field label="E-mail">
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="voce@exemplo.com"
                  required
                />
              </Field>
              <Field
                label="Senha"
                hint={
                  register
                    ? "Use uma senha com pelo menos 8 caracteres."
                    : undefined
                }
              >
                <input
                  name="password"
                  type="password"
                  autoComplete={register ? "new-password" : "current-password"}
                  minLength={register ? 8 : undefined}
                  required
                />
              </Field>
              <ErrorNotice error={error} />
              <Button disabled={pending} type="submit">
                {pending
                  ? "Aguarde…"
                  : register
                    ? "Solicitar acesso"
                    : "Entrar no MOVI+"}
                <ArrowRight size={18} />
              </Button>
              <p className="auth-switch">
                {register ? "Já tem uma conta?" : "Primeira vez por aqui?"}{" "}
                <Link to={register ? "/login" : "/solicitar-acesso"}>
                  {register ? "Entrar" : "Solicitar acesso"}
                </Link>
              </p>
            </form>
          )}
          <p className="auth-footer">
            Acesso reservado às equipes autorizadas.
            <br />
            Cada perfil acompanha somente suas rotinas.
          </p>
        </div>
      </main>
    </div>
  );
}
