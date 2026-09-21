import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

const sidebars: SidebarsConfig = {
  docs: [
    "intro",
    "getting-started",
    "project-structure",
    {
      type: "category",
      label: "Architecture",
      collapsed: false,
      items: [
        "architecture/overview",
        "architecture/request-flow",
        "architecture/ports-and-adapters",
        "architecture/errors",
        "architecture/testing",
      ],
    },
    {
      type: "category",
      label: "Guides",
      collapsed: false,
      items: [
        "guides/add-a-feature",
        "guides/replace-example-domain",
        "guides/change-database",
        "guides/extending",
      ],
    },
    {
      type: "category",
      label: "Decisions (ADR)",
      link: { type: "doc", id: "decisions/index" },
      items: [
        "decisions/001-feature-first-layout",
        "decisions/002-no-di-library",
        "decisions/003-no-mediator-no-cqrs",
        "decisions/004-transaction-per-request",
        "decisions/005-events-in-process",
        "decisions/006-stack",
        "decisions/007-validation-placement",
        "decisions/008-persistence-model",
        "decisions/009-authentication-as-adapter",
        "decisions/010-optimistic-concurrency",
      ],
    },
    "benchmark",
    "contributing",
  ],
};

export default sidebars;
