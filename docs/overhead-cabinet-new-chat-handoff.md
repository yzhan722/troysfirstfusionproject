# Overhead Cabinet — New Chat Handoff

Copy the block below into a **new Cursor chat** to continue this module without General Tall context pollution.

---

## Prompt (copy from here)

继续在当前 repo 的 `fusion360-unified-cabinet-plugin` 项目中开发 **Overhead Cabinet** generator module。

### 必读

1. `docs/overhead-cabinet-spec-v0.1.md` — 唯一权威 spec
2. `modules/overheadCabinet/` — 已搭好的 TS skeleton
3. `fusion360-cabinet-generator/core/overhead_geometry.py` — legacy 几何参考
4. `fusion360-cabinet-generator/tests/test_overhead_geometry.py` — golden case 来源

### 明确禁止

- 不要继承 General Tall 的 `style_1/style_2`、`V/T/H/VD`、clearance slot 等语义
- 不要从 General Tall chat 历史推断 overhead 规则
- 不要先改 Fusion body，先把 TS generator + tests 打通

### 当前状态

- skeleton 已存在：`types.ts`, `generator.ts`, `generator.test.ts`
- bridge 已存在：`scripts/overhead_from_params.js`, `tests/run_overhead_bridge_tests.js`
- `modules/overhead/controller.py` 已接 node bridge（placeholder generate）

### 下一步任务

1. 从 legacy Python 列出 overhead board taxonomy 和 feature 类型
2. 把 `overhead_geometry.py` 的规则逐步 port 到 `modules/overheadCabinet/generator.ts`
3. 为每个 legacy test case 写 TS golden test
4. 通过后再做 palette UI + Fusion adapter

### 验收标准

- `node modules/overheadCabinet/generator.test.ts` PASS
- `node fusion360-unified-cabinet-plugin/tests/run_overhead_bridge_tests.js` PASS
- 至少 3 个 legacy geometry case 与 Python 输出一致（允许浮点容差）

---

## Why a new chat

General Tall 历史包含大量专用语义（V-board matrix、T4/T5、VD notch 等）。新 chat 只携带 overhead spec，可避免模型误用 General Tall 规则。
