import { afterEach, beforeEach, it, expect, vi } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LessonDetail, AcademicList } from "./Academic";
import { today } from "./format";
const profile = vi.hoisted(() => ({ admin: true }));
vi.mock("./auth", () => ({
  useAuth: () => ({
    user: { roles: [profile.admin ? "secretary" : "instructor"] },
  }),
  isAdmin: () => profile.admin,
}));
beforeEach(() => {
  profile.admin = true;
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it.each([true, false])(
  "apresenta a listagem acadêmica como consulta no perfil de instrutor (turmas=%s)",
  async (classes) => {
    profile.admin = false;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              count: 0,
              next: null,
              previous: null,
              results: [],
            }),
          ),
        ),
      ),
    );
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <AcademicList classes={classes} />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByText("SEU DIÁRIO")).toBeInTheDocument();
    expect(
      screen.getByText(
        classes
          ? "Consulte as turmas e os encontros sob sua responsabilidade."
          : "Consulte as aulas e a chamada no seu diário autorizado.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("ROTINA DA SECRETARIA")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: classes ? "Nova turma" : "Nova aula",
      }),
    ).not.toBeInTheDocument();
    await screen.findByText(/Nenhum registro disponível no escopo/);
  },
);
it("expõe a decisão pendente e impede conclusão de chamada mesmo com marcações completas", async () => {
  const fetcher = vi.fn().mockImplementation((path: string) =>
    Promise.resolve(
      new Response(
        JSON.stringify(
          path.includes("/roster/")
            ? {
                lesson: 1,
                version: "snapshot-test",
                participants: [
                  { enrollment: 7, student_name: "Participante de teste" },
                ],
                excluded: [],
                decisions: ["DN-014"],
              }
            : {
                id: 1,
                class_name: "Turma de teste",
                date: today(),
                instructor_name: "Instrutor de teste",
                status: "scheduled",
                notes: "",
              },
        ),
      ),
    ),
  );
  vi.stubGlobal("fetch", fetcher);
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={["/aulas/1"]}>
        <Routes>
          <Route path="/aulas/:id" element={<LessonDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(
    await screen.findByText(/Chamada indisponível: decisões institucionais/),
  ).toBeInTheDocument();
  expect(screen.getByText(/DN-014/)).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Concluir chamada e aula" }),
  ).toBeDisabled();
  expect(screen.getByLabelText("Presente")).toBeDisabled();
  fireEvent.click(
    screen.getByRole("button", { name: "Concluir chamada e aula" }),
  );
  expect(
    fetcher.mock.calls.every(
      (call) => !String(call[0]).includes("/attendance/"),
    ),
  ).toBe(true);
});
it("consulta marcações originais de aula concluída sem recalcular o roster atual", async () => {
  const fetcher = vi.fn().mockImplementation((path: string) =>
    Promise.resolve(
      new Response(
        JSON.stringify(
          path.includes("/attendance/")
            ? {
                lesson: 1,
                status: "completed",
                definition: "Marcações gravadas na conclusão.",
                marks: [
                  {
                    enrollment: 7,
                    student_name: "Participante histórico de teste",
                    present: true,
                    created_at: "2026-10-07T12:00:00Z",
                  },
                ],
              }
            : {
                id: 1,
                class_name: "Turma de teste",
                date: today(),
                instructor_name: "Instrutor de teste",
                status: "completed",
                notes: "",
              },
        ),
      ),
    ),
  );
  vi.stubGlobal("fetch", fetcher);
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={["/aulas/1"]}>
        <Routes>
          <Route path="/aulas/:id" element={<LessonDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(
    await screen.findByText("Participante histórico de teste"),
  ).toBeInTheDocument();
  expect(screen.getByText("Presente")).toBeInTheDocument();
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  expect(
    fetcher.mock.calls.every((call) => !String(call[0]).includes("/roster/")),
  ).toBe(true);
});
