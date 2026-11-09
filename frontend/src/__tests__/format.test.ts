import { confidenceLabel, formatINR } from "../lib/format";

describe("formatINR", () => {
  it("formats integer paise with Indian grouping", () => {
    expect(formatINR(77760)).toBe("₹777.60");
    expect(formatINR(984550)).toBe("₹9,845.50");
    expect(formatINR(1_00_00_000)).toBe("₹1,00,000.00");
    expect(formatINR(0)).toBe("₹0.00");
  });
  it("handles negatives", () => expect(formatINR(-30450)).toBe("-₹304.50"));
});

describe("confidenceLabel", () => {
  it("buckets confidence", () => {
    expect(confidenceLabel(0.95)).toBe("high");
    expect(confidenceLabel(0.75)).toBe("medium");
    expect(confidenceLabel(0.6)).toBe("low");
  });
});
