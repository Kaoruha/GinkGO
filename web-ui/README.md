# Ginkgo Web UI

Vue 3 + TypeScript + shadcn-vue + Tailwind CSS 前端（技术栈以顶层 README 及 `package.json` 为准）。

## 开发

```bash
pnpm install
pnpm dev
```

启动命令：`ginkgo serve webui`

## 测试

E2E 测试位于项目根目录 `tests/e2e/`，使用 Python + pytest + Playwright，不在本目录内。

```bash
pytest tests/e2e/ -v
```

## 构建

```bash
pnpm build
```
