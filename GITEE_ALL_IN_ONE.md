# 全 Gitee 托管方案 (Gitee 代码 + Gitee Action + Gitee Pages)

如果你希望**所有数据、代码、流水线和网页**都在 Gitee (码云) 上，不依赖任何外部平台，请遵循此教程。

## 1. 准备工作

确保你的代码主要分支是 `main`。

## 2. 启用 Gitee Pages

1.  登录 Gitee，进入你的仓库页面。
2.  点击顶部菜单 **“服务”** -> **“Gitee Pages”**。
3.  **部署分支**选择 `main`。
4.  **部署目录**填写 `docs` (非常重要，因为我们的网页在 docs 目录下)。
5.  点击 **“启动”** 或 **“更新”**。
6.  记下生成的网站地址。

## 3. 开通 Gitee Actions (Beta)

目前 Gitee Actions 是公测功能。
1.  进入仓库首页。
2.  点击 **“流水线”** 或 **“Actions”** 标签。
3.  如果提示需要开通，请点击申请（通常秒过）。

## 4. 配置环境变量 (Secrets/Variables)

为了让自动化脚本运行，我们需要配置三个敏感信息。

1.  进入仓库 **“设置”** -> **“环境变量”** (或者流水线设置里的密钥)。
2.  添加以下变量（注意选择 **“密钥/Secret”** 类型，不要明文显示）：

| 变量名 | 内容 | 用于 |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | `sk-xxxxxx` | 爬虫调用 LLM 生成摘要 |
| `WEBHOOK_URL` | `https://...` | (可选) 推送通知 |
| `GITEE_USERNAME` | `<你的Gitee账号名>` | 登录 Gitee Pages |
| `GITEE_PASSWORD` | `<你的Gitee登录密码>` | **必需**。用于自动触发 Pages 更新 |

> **为什么需要密码？**
> Gitee Pages 免费版**不支持**自动部署。我们使用了一个开源的 Action (`yanglbme/gitee-pages-action`)，它是通过模拟浏览器登录你的账号去点击“更新”按钮的。如果不填密码，你需要每天自己去点一次更新。

## 5. 推送代码

```bash
git add .gitee/workflows/daily_crawl.yml
git commit -m "feat: migrate to gitee actions"
git push origin main
```

## 6. 验证

1.  推送后，点击仓库的 **“流水线” (Actions)** 标签。
2.  你应该能看到 `Daily Policy Crawl (Gitee)` 开始运行。
3.  等待几分钟，如果全部变绿：
    *   爬虫成功抓取数据。
    *   代码成功提交回仓库。
    *   Gitee Pages 成功自动刷新。

---
**注意事项**：
*   如果 `Deploy to Gitee Pages` 步骤失败（通常是因为验证码拦截），你可能需要手动去 Gitee Pages 页面点一下更新。
*   Gitee 如果检测到通过脚本频繁登录，可能会暂时冻结账号的自动登录功能，建议设置定时任务频率不要太高（目前是一天一次，通常没问题）。
