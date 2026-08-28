# 仓库展示：去外部依赖 + Actions 生成数据/预览图 + 修复中文字体

## 回答你的两个疑问
1. **后端依赖**：页面本身仍是纯静态，但目前运行时请求 GitHub 两个公共服务（api.github.com 数据、opengraph.githubassets.com 预览图），确实存在外部依赖。
2. **限流**：会。两个服务都按访客 IP 限流（API 60 次/时、图片 100 次/时），同 IP 访客多或被爬虫盯上就会触发，届时卡片退化（描述缺失、图片变占位块）。localStorage 缓存只救得了回头客，救不了冷启动。

## 解法：部署时由 Actions 生成数据与预览图（零提交、零外部依赖）
在现有部署 workflow 里加一步构建：**每次 push + 每 6 小时定时**，CI 服务端拉一次 GitHub API（用自带 GITHUB_TOKEN，认证额度 5000 次/时，与访客 IP 无关），生成：
- `repos/repos.json`：瘦身后的仓库数据（名称/描述/链接/语言及颜色/星标/topics/fork/archived/更新时间）
- `repos/previews/<仓库名>.png`：**自绘预览图**（Pillow + Noto Sans CJK，金色主题与站点一致，正确渲染中文，含语言色点、★ 星标、Fork/已归档徽标）——同时解决中文字体问题

产物直接进部署工件，**不产生任何 git 提交**（避免用 GITHUB_TOKEN 推送不触发部署的坑，也不膨胀 git 历史）。线上页面只加载同源静态文件，api.github.com 和 opengraph.githubassets.com 请求全部消失。

## 改动清单
1. 新建 `.github/scripts/build_repos.py`：拉 API → 写 JSON → 自绘预览图 → 清理已删仓库的旧图；字体自动适配 Ubuntu(Noto CJK)/Windows(微软雅黑)/macOS(PingFang)，本地也能跑（支持传入已下载的 JSON 离线生成）。
2. 修改 `.github/workflows/static.yml`：加 `schedule: 0 */6 * * *` 触发；Checkout 后、上传工件前加构建步骤（setup-python → pip install pillow → 运行脚本，注入 GITHUB_TOKEN）。
3. 改 `js/repos.js`：数据源改为 `/repos/repos.json`，图片改为 `/repos/previews/<名>.png`；**删除 localStorage 缓存层和语言颜色表**（颜色由 JSON 提供，限流不复存在，代码更简）；保留图片 onerror 占位块和错误卡片兜底。两个 html 中 repos.js 版本号升 `?v=1.0.3`。
4. `.gitignore` 增加 `repos/repos.json` 与 `repos/previews/`（生成物不进 git）。
5. 本地跑一次脚本生成数据与图片，浏览器复测：卡片渲染、新预览图中文字体效果截图确认、确认页面不再发起任何 GitHub 公共服务请求。按此前要求，全部改动只留本地不提交。

## 部署后效果
push 上线后 workflow 自动生效：每 6 小时与每次 push 都会重新拉取数据并部署，新建仓库最迟 6 小时后出现（也可在 Actions 页手动 Run workflow 立即刷新）。页面运行时外部请求只剩你原有的 COS 背景图（带本地兜底）和备案图标。