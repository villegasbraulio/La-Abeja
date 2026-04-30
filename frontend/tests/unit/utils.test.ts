import { formatARS, formatDate, slugify } from "../../src/lib/utils";

describe("formatARS", () => {
  it("formats prices in Argentine pesos", () => {
    expect(formatARS("18500")).toContain("$");
  });
});

describe("slugify", () => {
  it("normalizes accents and spaces", () => {
    expect(slugify("Gran Malbec Ícono")).toBe("gran-malbec-icono");
  });
});

describe("formatDate", () => {
  it("formats ISO dates for es-AR", () => {
    expect(formatDate("2026-04-30T12:00:00.000Z")).toContain("2026");
  });
});
