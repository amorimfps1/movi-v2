import { describe, it, expect } from "vitest";
import { date, money, label } from "./format";
import { isAdmin } from "./auth";
import type { User } from "./types";
describe("apresentação do domínio", () => {
  it("preserva data civil sem deslocamento de fuso", () => {
    expect(date("2026-10-07")).toBe("07/10/2026");
    expect(date("2026-01-01")).toBe("01/01/2026");
    expect(date(null)).toBe("—");
  });
  it("apresenta centavos em reais", () => {
    expect(money("1234.56")).toContain("1.234,56");
    expect(money(null)).toBe("—");
  });
  it("não apresenta decisão pendente como participação liberada", () => {
    expect(label("decision_required")).toBe("Decisão pendente");
  });
  it("restringe ações administrativas por função", () => {
    const user = { roles: ["instructor"] } as User;
    expect(isAdmin(user)).toBe(false);
    expect(isAdmin({ ...user, roles: ["communication"] })).toBe(false);
    expect(isAdmin({ ...user, roles: ["secretary"] })).toBe(true);
    expect(isAdmin(null)).toBe(false);
  });
});
