import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import hooks from 'eslint-plugin-react-hooks';
export default tseslint.config(
 {ignores:['node_modules/**','.next/**','test-results/**','playwright-report/**','components/legacy-workspace.tsx','next-env.d.ts']},
 eslint.configs.recommended,
 ...tseslint.configs.recommended,
 {files:['**/*.{ts,tsx}'],plugins:{'react-hooks':hooks},rules:{'react-hooks/rules-of-hooks':'error','@typescript-eslint/no-unused-vars':['error',{argsIgnorePattern:'^_',varsIgnorePattern:'^_'}],'@typescript-eslint/no-explicit-any':'error','no-eval':'error'}}
);
