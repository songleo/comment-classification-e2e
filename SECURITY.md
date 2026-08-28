# 安全策略

## 报告安全问题

请不要在公开 Issue 中披露尚未修复的安全漏洞。优先使用 GitHub 的 [Private vulnerability reporting](https://github.com/songleo/comment-classification-e2e/security/advisories/new) 私下报告。

报告建议包含受影响的提交或镜像摘要、最小复现步骤、潜在影响和已经验证的缓解方式。不要提交真实客户评论、访问令牌、私钥或其他敏感数据。

## 支持范围

本项目采用 Docker-only 交付，当前支持范围包括仓库中的 Dockerfile、Compose 配置、发布镜像构建方式、API 代码和 Kubernetes 示例清单。

示例清单不自动提供生产级 TLS、认证、授权、网络策略、镜像签名、漏洞扫描、秘密管理、容量规划或监控告警。部署方必须在自己的镜像仓库与集群中单独验证这些能力；没有证据时状态为 `UNKNOWN`。

发布时应使用不可变镜像摘要，避免仅依赖可变标签。基础镜像、Python 包和基础模型继续适用各自的安全公告与升级策略。
