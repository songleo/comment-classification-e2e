# Docker 验证记录

## 验证范围

验证日期为 2026-08-29（Asia/Shanghai）。本次只使用标准 Docker CLI，从镜像构建开始，执行容器内代码规范检查、单元测试、数据校验、CPU 训练、独立测试评估、CLI 推理、本地 API、发布镜像、远端镜像和 Kubernetes 清单 schema 验收。

宿主机 Python、curl、kubectl、绝对路径和额外容器编排工具不属于本地交付前提。模型、报告和基础模型缓存使用 Docker 命名卷保存。Docker Hub 发布、清单 schema 校验和 Kubernetes 集群部署是独立阶段，状态单独记录。

维护者随后在提交 `3e5c48b62a0eed80296fc2af291413d2374d917a` 上，按 [README](../README.md)“方式 A”的命令顺序手工完成开发镜像构建、两个命名卷创建、完整 E2E、API 健康检查、容器内 `/health` 与 `/predict` 调用以及 API 容器清理，并确认全部通过。

## 容器环境

| 项目 | 实测值 |
| --- | --- |
| Docker Engine | 29.6.2，Linux amd64 |
| Docker Desktop | 4.85.0 |
| 基础镜像来源 | DaoCloud Docker Hub 代理 |
| 基础镜像 | Python 3.13.15 slim |
| 基础镜像摘要 | `sha256:7ce4b6dfe35e55397b7cda544f8a13f191b7ae28dc5aad71fe664dbc9bc2623f` |
| Python | 3.13.15 |
| PyTorch | `2.8.0+cpu` |
| CUDA 可用 | `False` |
| Pydantic Core | 2.33.2 |
| NumPy | 2.3.2 |
| Python 包来源 | 阿里云 PyPI 与阿里云 PyTorch CPU wheels |
| 基础模型来源 | `hf-mirror.com` |
| 基础模型 | `hfl/rbt3` |
| 基础模型 revision | `0412ffdc25bf738c556d523f8553bd69efe6405b` |

## 验证结论

| 阶段 | 状态 | 实际证据 |
| --- | --- | --- |
| 开发镜像直接构建 | PASS | `docker build` 成功，Python 3.13.15 与 CPU-only PyTorch 可用 |
| 维护者手工复核 | PASS | 在提交 `3e5c48b` 上逐条执行 README 方式 A 的本地构建、E2E、API 验证和清理命令，确认全部通过 |
| Ruff | PASS | `All checks passed!` |
| Pytest | PASS | `7 passed` |
| 数据校验 | PASS | train 500、validation 120、test 120；四类均衡且跨集合无重复 |
| 真实训练 | PASS | CPU 完成 5 epochs，保存最佳模型与同一 tokenizer |
| 独立测试评估 | PASS | 生成 JSON、CSV 和 Markdown 报告 |
| CLI 推理 | PASS | “客服一直不处理退款”预测为 `complaint` |
| Docker 命名卷 | PASS | 模型、报告和基础模型缓存不依赖宿主机路径 |
| 直接 Docker API | PASS | 容器达到 `healthy`，`/health` 与 `/predict` 返回成功 |
| 模型导出 | PASS | `docker create` 与 `docker cp` 从命名卷复制模型到相对构建目录 |
| 发布镜像构建 | PASS | `songleo/comment-classification-e2e:0.1.0` 本地构建成功 |
| 发布镜像独立运行 | PASS | 不挂载源码或模型卷时容器 `healthy`，接口返回成功 |
| Docker Hub 发布 | PASS | `songleo/comment-classification-e2e:0.1.0` 已发布，摘要为 `sha256:a971d00cc98932d08be4de1f65e14fc3af9dcdd3f768079ce14e472495c10b22` |
| Docker Hub 远端运行 | PASS | 直接 pull 后容器 `healthy`；`/health` 和 `/predict` 均成功，远端模型版本为 `20260828T234758Z` |
| 国内加速入口 | PASS | `docker.1ms.run/songleo/comment-classification-e2e:0.1.0` 拉取成功，与 Docker Hub 镜像 ID 相同，接口复测成功 |
| Kubernetes 清单 schema | PASS | `kubeconform v0.7.0` 在 Docker 中检查 2 个资源：Valid 2、Invalid 0、Errors 0、Skipped 0 |
| Kubernetes 集群 | UNKNOWN | 没有获批集群、服务端 dry-run、rollout 或集群接口证据 |

## 训练与评估结果

| 指标 | 结果 |
| --- | ---: |
| 最佳验证宏平均 F1 | 1.000 |
| 测试准确率 | 0.958333 |
| 测试宏平均 F1 | 0.957685 |
| 投诉召回率 | 1.000 |
| 投诉召回率门槛 | 0.700，PASS |
| 本地本次训练模型版本 | `20260829T014541Z` |
| Docker Hub 发布模型版本 | `20260828T234758Z` |

## 复现命令

```console
docker build --tag comment-classifier-dev:0.1.0 .
docker volume create comment-classifier-artifacts
docker volume create comment-classifier-huggingface-cache
docker run --rm --name comment-classifier-e2e --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts --mount type=volume,source=comment-classifier-huggingface-cache,target=/cache/huggingface --env HF_ENDPOINT=https://hf-mirror.com comment-classifier-dev:0.1.0 /bin/sh /app/scripts/run-e2e.sh
docker run --detach --name comment-classifier-api --publish 8000:8000 --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts,readonly comment-classifier-dev:0.1.0
docker inspect --format "{{.State.Health.Status}}" comment-classifier-api
docker run --rm --network container:comment-classifier-api comment-classifier-dev:0.1.0 python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/health').json())"
docker run --rm --network container:comment-classifier-api comment-classifier-dev:0.1.0 python -c "import httpx; print(httpx.post('http://127.0.0.1:8000/predict', json={'text':'客服一直不处理退款'}).json())"
docker stop comment-classifier-api
docker rm comment-classifier-api
docker create --name comment-classifier-model-export --mount type=volume,source=comment-classifier-artifacts,target=/source comment-classifier-dev:0.1.0
docker cp comment-classifier-model-export:/source/model/. ./artifacts/model
docker rm comment-classifier-model-export
docker build --file Dockerfile.release --tag songleo/comment-classification-e2e:0.1.0 .
docker run --detach --name comment-classifier-release --publish 8000:8000 songleo/comment-classification-e2e:0.1.0
docker inspect --format "{{.State.Health.Status}}" comment-classifier-release
docker run --rm --network container:comment-classifier-release songleo/comment-classification-e2e:0.1.0 python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')))"
docker run --rm --network container:comment-classifier-release songleo/comment-classification-e2e:0.1.0 python -c "import json,urllib.request; request=urllib.request.Request('http://127.0.0.1:8000/predict',data=json.dumps({'text':'\u5ba2\u670d\u4e00\u76f4\u4e0d\u5904\u7406\u9000\u6b3e'}).encode(),headers={'Content-Type':'application/json'}); print(json.load(urllib.request.urlopen(request)))"
docker stop comment-classifier-release
docker rm comment-classifier-release
```

只验证发布镜像时，可以按 [README](../README.md) 直接拉取 Docker Hub 镜像；下载较慢或代理不支持该仓库时，使用文档中已验证的国内加速入口。

## 结论边界

本次 PASS 证明当前 Docker CPU 链路、合成数据、模型训练、评估、推理、本地 API、发布镜像、Docker Hub 拉取运行和清单 schema 校验闭环。它不能证明真实业务准确率，也不能替代 Kubernetes 集群、TLS、认证、容量、监控、漏洞扫描、签名或回滚验收。
