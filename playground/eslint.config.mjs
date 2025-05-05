// @ts-check
import eslint from "@eslint/js";
import eslintConfigPrettier from "eslint-config-prettier/flat";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tsEslint from "typescript-eslint";

export default tsEslint.config(
  eslint.configs.recommended,
  tsEslint.configs.recommended,
  reactRefresh.configs.recommended,
  reactHooks.configs["recommended-latest"], // Change to recommended when v6 releases
  eslintConfigPrettier,
  {
    rules: {
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": "error",
      "no-undef": "error",
      "prefer-const": "error",
      "no-console": "warn",
    },
  },
  { languageOptions: { globals: globals.browser } },
  { ignores: ["**/dist"] },
  { files: ["**/*.{ts.tsx}"] }, // JS files are included by default
  { linterOptions: { reportUnusedDisableDirectives: "error" } },
);
