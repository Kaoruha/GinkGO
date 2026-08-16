import js from '@eslint/js'
import { defineConfig, globalIgnores } from 'eslint/config'
import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import vueParser from 'vue-eslint-parser'
import globals from 'globals'

export default defineConfig(
  globalIgnores(['**/dist', '**/out', '**/node_modules', 'coverage', '*.config.js', '*.config.ts', 'pdp_*.mjs']),
  {
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
  },
  js.configs.recommended,
  pluginVue.configs['flat/recommended'],
  tseslint.configs.recommended,
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
  },
  {
    rules: {
      'vue/multi-word-component-names': 'off',
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
        },
      ],
      'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
      'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    },
  },
  {
    // ParamFields 的 config prop 为引用共享变异(与原 v-model="item.config[param.name]"
    // 等价,父级 formData 同步感知),规则误报故对该文件关闭
    files: ['src/renderer/components/common/ParamFields.vue'],
    rules: {
      'vue/no-mutating-props': 'off',
    },
  },
)
