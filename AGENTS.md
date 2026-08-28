# 项目工作规则

## 项目目标

构建一个可复现的中文电商评论分类项目，通过标准 Docker CLI 完整覆盖数据集校验、Transformer 微调、评估、推理、API 服务、发布镜像和 Kubernetes 部署资料。

## 范围与边界

- 分类标签固定为 `positive`、`negative`、`neutral` 和 `complaint`。
- 项目数据是合成演示数据，不包含个人信息。
- 基础模型与 revision 固定在 `configs/train.json`。
- 唯一支持的交付和运行方式是 Docker；不得新增宿主机 Python、虚拟环境或直接运行 API 的文档路径。
- 本地文档不假设 Windows、Linux、macOS、PowerShell、WSL 或特定终端；所有操作必须是标准、单行 Docker CLI 命令。
- 本项目不依赖额外的容器编排工具。
- 开发与训练容器固定使用 `python:3.13.15-slim`，项目 Python 约束为 `>=3.13.15,<3.14`。
- 当前容器交付固定使用 PyTorch 2.8.0 CPU 轮子；GPU/CUDA 不在默认范围内。
- 没有真实证据时，不得声称已经完成镜像仓库、生产环境或 Kubernetes 验证。
- 不得提交基础模型缓存、训练模型、虚拟环境或本地评估产物。

## 必须执行的验证

用户已取得源码并进入项目根目录后，只需要可用的 Docker Engine：

```console
docker version
docker build --tag comment-classifier-dev:0.1.0 .
docker volume create comment-classifier-artifacts
docker volume create comment-classifier-huggingface-cache
docker run --rm --name comment-classifier-e2e --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts --mount type=volume,source=comment-classifier-huggingface-cache,target=/cache/huggingface --env HF_ENDPOINT=https://hf-mirror.com comment-classifier-dev:0.1.0 /bin/sh /app/scripts/run-e2e.sh
docker run --detach --name comment-classifier-api --publish 8000:8000 --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts,readonly comment-classifier-dev:0.1.0
docker inspect --format "{{.State.Health.Status}}" comment-classifier-api
docker logs comment-classifier-api
docker run --rm --network container:comment-classifier-api comment-classifier-dev:0.1.0 python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/health').json())"
docker stop comment-classifier-api
docker rm comment-classifier-api
```

构建发布镜像前，使用临时 Docker 容器把已验证模型复制到仓库的相对构建目录：

```console
docker create --name comment-classifier-model-export --mount type=volume,source=comment-classifier-artifacts,target=/source comment-classifier-dev:0.1.0
docker cp comment-classifier-model-export:/source/model/. ./artifacts/model
docker rm comment-classifier-model-export
docker build --file Dockerfile.release --tag comment-classifier:validation .
```

完成标准：开发镜像构建成功；代码规范检查和测试通过；三个数据集通过校验；训练生成可重新加载的模型与 tokenizer；评估生成机器可读和人工可读报告；CLI 推理成功；API 容器健康；发布镜像可以从同一模型产物构建。

Kubernetes 只允许先做客户端或服务端 dry-run；没有获批集群和镜像仓库时，不得实际发布，也不得记录为已验证。

## 项目约定

- 一般说明文档默认使用中文；代码、命令、路径、接口字段和技术名称除外。
- 公开文档不得包含维护者本机的用户名、盘符、绝对工作区路径或终端提示符。
- 所有用户示例必须通过 Docker 或 Kubernetes 运行容器，不得要求宿主机 Python 或特定终端功能。
- 本地验证步骤不得依赖额外的容器编排工具。
- 使用 UTF-8；公共函数应提供类型标注。
- 严格、确定性地隔离训练集、验证集和测试集。
- 训练和服务必须使用训练产物中保存的同一个 tokenizer。
- 重要技术选择和限制记录在 `docs/DECISIONS.md`。
