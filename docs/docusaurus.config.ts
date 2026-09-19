import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";
import { themes as prismThemes } from "prism-react-renderer";

const organization = "davidcohenDC";
const pagesHost = "davidcohendc.github.io";
const project = "python-clean-architecture-template";

const config: Config = {
  title: "Python Clean Architecture Template",
  tagline: "A pragmatic, test-enforced Clean Architecture starter for Python APIs",
  favicon: "img/favicon.svg",

  url: `https://${pagesHost}`,
  baseUrl: `/${project}/`,
  organizationName: organization,
  projectName: project,
  trailingSlash: false,

  onBrokenLinks: "throw",

  markdown: { mermaid: true, hooks: { onBrokenMarkdownLinks: "warn" } },
  themes: ["@docusaurus/theme-mermaid"],

  i18n: { defaultLocale: "en", locales: ["en"] },

  presets: [
    [
      "classic",
      {
        docs: {
          routeBasePath: "/",
          sidebarPath: "./sidebars.ts",
          editUrl: `https://github.com/${organization}/${project}/edit/main/docs/`,
        },
        blog: false,
        theme: { customCss: "./src/css/custom.css" },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: { respectPrefersColorScheme: true },
    navbar: {
      title: "Clean Architecture Template",
      items: [
        { type: "docSidebar", sidebarId: "docs", position: "left", label: "Docs" },
        { to: "/decisions", label: "Decisions", position: "left" },
        { href: `https://github.com/${organization}/${project}`, label: "GitHub", position: "right" },
      ],
    },
    footer: {
      style: "dark",
      links: [
        {
          title: "Learn",
          items: [
            { label: "Getting started", to: "/getting-started" },
            { label: "Architecture", to: "/architecture/overview" },
            { label: "Replace the example domain", to: "/guides/replace-example-domain" },
          ],
        },
        {
          title: "Project",
          items: [
            { label: "GitHub", href: `https://github.com/${organization}/${project}` },
            { label: "Issues", href: `https://github.com/${organization}/${project}/issues` },
            { label: "Changelog", href: `https://github.com/${organization}/${project}/blob/main/CHANGELOG.md` },
          ],
        },
      ],
      copyright: `MIT licensed. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ["python", "bash", "toml", "docker", "json"],
    },
    mermaid: { theme: { light: "neutral", dark: "dark" } },
  } satisfies Preset.ThemeConfig,
};

export default config;
