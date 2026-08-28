# Docker 验证记录

## 验证范围

验证日期为 2026-08-28（Asia/Shanghai）。本次从 Docker 镜像构建开始，实际执行容器内代码规范检查、单元测试、数据校验、CPU 训练、独立测试评估、CLI 推理、Compose API 和发布镜像验收。

宿主机 Python 不属于交付环境。Docker Hub 推送和 Kubernetes 是独立阶段，状态单独记录。

## 容器环境

| 项目 | 实测值 |
| --- | --- |
| Docker Engine | 29.6.2，Linux amd64 |
| Docker Compose | 5.3.1 |
| 基础镜像来源 | DaoCloud Docker Hub 代理 |
| 基础镜像 | Python 3.13.15 slim |
| 基础镜像摘要 | `sha256:7ce4b6dfe35e55397b7cda544f8a13f191b7ae28dc5aad71fe664dbc9bc2623f` |
| Python | 3.13.15 |
| PyTorch | `2.8.0+cpu` |
| CUDA 可用 | `False` |
| Pydantic Core | 2.33.2，Python 3.13 Linux 轮子 |
| NumPy | 2.3.2，Python 3.13 Linux 轮子 |
| Python 包来源 | 阿里云 PyPI 与阿里云 PyTorch CPU wheels |
| 基础模型来源 | `hf-mirror.com` |
| 基础模型 | `hfl/rbt3` |
| 基础模型 revision | `0412ffdc25bf738c556d523f8553bd69efe6405b` |

## 验证结论

| 阶段 | 状态 | 实际证据 |
| --- | --- | --- |
| 开发镜像构建 | PASS | Python 3.13.15 与 CPU-only PyTorch 镜像构建成功 |
| Ruff | PASS | `All checks passed!` |
| Pytest | PASS | `4 passed` |
| 数据校验 | PASS | train 500、validation 120、test 120；四类均衡且跨集合无重复 |
| 真实训练 | PASS | CPU 完成 5 epochs，保存最佳模型与同一 tokenizer |
| 独立测试评估 | PASS | 生成 JSON、CSV 和 Markdown 报告 |
| CLI 推理 | PASS | “客服一直不处理退款”预测为 `complaint` |
| Compose API | PASS | 容器 `healthy`，`/health` 与 `/predict` 返回成功 |
| 发布镜像构建 | PASS | `songleo/comment-classification-e2e:0.1.0` 本地构建成功 |
| 发布镜像独立运行 | PASS | 不挂载源码或模型目录时容器 `healthy`，接口返回成功 |
| Docker Hub 推送 | BLOCKED | `registry-1.docker.io:443` 直连超时；Docker Desktop 没有可用 HTTPS proxy，远端 digest 尚未产生 |
| Kubernetes | UNKNOWN | 没有获批集群、服务端 dry-run、rollout 或接口证据 |

## 训练与评估结果

| 指标 | 结果 |
| --- | ---: |
| 最佳验证宏平均 F1 | 1.000 |
| 测试准确率 | 0.958333 |
| 测试宏平均 F1 | 0.957685 |
| 投诉召回率 | 1.000 |
| 投诉召回率门槛 | 0.700，PASS |
| 模型版本 | `20260828T150307Z` |

测试混淆矩阵固定顺序为 positive、negative、neutral、complaint：

```text
[[26, 2, 1, 1],
 [0, 29, 1, 0],
 [0, 0, 30, 0],
 [0, 0, 0, 30]]
```

CLI 和两个 API 容器对“客服一直不处理退款”均返回：

```json
{
  "label": "complaint",
  "confidence": 0.998949,
  "model_version": "20260828T150307Z"
}
```

## 发布镜像

本地发布镜像标签为 `songleo/comment-classification-e2e:0.1.0`，本地镜像大小约 561 MB，构建时的本地 manifest list 摘要为：

```text
sha256:9e432158ddeea48b3ec0ec5c559053dc7891f1cc8bdf12f5d70485f7c1494e1a
```

该值是本地 BuildKit 输出，不是 Docker Hub 远端 digest。远端推送成功后，必须用 Docker Hub 返回的 digest 更新本节和 `deploy/kubernetes.yaml`。

## 复现命令

```powershell
docker compose build
docker compose run --rm -e HF_ENDPOINT=https://hf-mirror.com e2e
docker compose up -d api
docker compose ps
docker compose down
docker build -f Dockerfile.release -t songleo/comment-classification-e2e:0.1.0 .
```

只验证发布镜像时，可以按 [README](../README.md) 直接拉取 Docker Hub 镜像；在当前远端推送完成前，该路径仍不可用。

## 结论边界

本次 PASS 只证明当前 Docker CPU 链路、合成数据、模型训练、评估、推理和本地 API 闭环。它不能证明真实业务准确率，也不能替代 Docker Hub 推送、Kubernetes、TLS、认证、容量、监控、漏洞扫描、签名或回滚验收。
