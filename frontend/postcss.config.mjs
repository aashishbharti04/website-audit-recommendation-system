import { fileURLToPath } from "url";
import path from "path";

// Point Tailwind at this project's config explicitly. Without this, the plugin
// searches from process.cwd() — which breaks when `next dev` is launched from a
// different directory (it would silently fall back to an empty default config).
const dir = path.dirname(fileURLToPath(import.meta.url));

export default {
  plugins: {
    tailwindcss: { config: path.join(dir, "tailwind.config.ts") },
    autoprefixer: {},
  },
};
