import { describe, expect, it } from "vitest";

import { styleGuideOverviewSchema } from "@/features/style-guide/schema";
import { styleGuideOverviewMock } from "@/mocks/data";

describe("styleGuideOverviewSchema", () => {
  it("validates the POC overview payload", () => {
    const overview = styleGuideOverviewSchema.parse(styleGuideOverviewMock);

    expect(overview.activePack).toBeNull();
    expect(overview.currentWorkflow).toBeNull();
    expect(overview.metrics.activeRules).toBe(0);
  });
});
