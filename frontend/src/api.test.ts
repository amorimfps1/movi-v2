import { afterEach, describe, it, expect, vi } from "vitest";
import { api, post, ApiError, optionsFor } from "./api";
afterEach(() => vi.restoreAllMocks());
describe("contrato da API", () => {
  it("apresenta404 em português sem revelar o nome interno do modelo", () => {
    const data = {
      detail: "No Lesson matches the given query.",
      code: "not_found",
    };
    const error = new ApiError(404, data);
    expect(error.message).toBe(
      "Registro não encontrado ou indisponível para seu perfil.",
    );
    expect(error.message).not.toContain("Lesson");
    expect(error.data).toEqual(data);
    expect(error.status).toBe(404);
  });
  it("preserva erro institucional e IDs de decisão", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: "Política de cobertura pendente.",
            decisions: ["DN-004"],
          }),
          { status: 409, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    try {
      await api("enrollments/1/eligibility/");
      throw new Error("Deveria falhar");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(409);
      expect((error as ApiError).data.decisions).toEqual(["DN-004"]);
    }
  });
  it("usa sessão e token CSRF nas gravações", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ csrfToken: "secure-token" })),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 1 })));
    vi.stubGlobal("fetch", fetcher);
    await post("students/", { name: "Pessoa" });
    expect(fetcher).toHaveBeenLastCalledWith(
      "/api/students/",
      expect.objectContaining({
        credentials: "same-origin",
        method: "POST",
        headers: expect.objectContaining({ "X-CSRFToken": "secure-token" }),
      }),
    );
  });
  it("carrega todas as páginas nas opções de vínculo", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              results: [{ id: 1 }],
              next: "/api/classes/?page=2",
            }),
          ),
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ results: [{ id: 2 }], next: null })),
        ),
    );
    expect(await optionsFor("classes/")).toHaveLength(2);
  });
  it("não converte falha de conexão em lista vazia", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(api("students/")).rejects.toThrow("conectar");
  });
});
