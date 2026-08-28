# 安全策略

## 报告安全问题

请不要在公开 Issue 中披露尚未修复的安全漏洞。优先使用 GitHub 的
[Private vulnerability reporting](https://github.com/songleo/comment-classification-e2e/security/advisories/new)
私下提交报告。

报告中建议包含：

- 受影响的提交、版本或文件；
- 可复现步骤和必要的最小示例；
- 可能造成的影响；
- 已验证的缓解方式（如有）。

请勿在报告中提交真实客户评论、访问令牌、私钥或其他敏感数据。

## 支持范围

该项目目前是本地学习和工程验证示例，没有发布稳定版本，也没有生产环境安全承诺。维护者
会优先处理当前 `main` 分支中可复现的问题。Docker、Kubernetes、网络入口、TLS、认证、
授权和生产监控需要由实际部署环境单独设计与验证。
