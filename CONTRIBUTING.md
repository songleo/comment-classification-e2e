# 贡献指南

本项目只接受可通过标准 Docker CLI 复现的交付流程。取得源码并进入项目根目录后，贡献者只需要 Docker，不需要宿主机 Python、curl 或特定终端。

## 构建开发镜像

```console
docker build --tag comment-classifier-dev:0.1.0 .
```

## 提交前验证

Docker 命名卷让模型、报告和基础模型缓存独立于宿主机路径与操作系统：

```console
docker volume create comment-classifier-artifacts
docker volume create comment-classifier-huggingface-cache
docker run --rm --name comment-classifier-e2e --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts --mount type=volume,source=comment-classifier-huggingface-cache,target=/cache/huggingface --env HF_ENDPOINT=https://hf-mirror.com comment-classifier-dev:0.1.0 /bin/sh /app/scripts/run-e2e.sh
```

修改 API、容器或部署文件时，还必须直接启动容器并检查健康状态、日志和接口：

```console
docker run --detach --name comment-classifier-api --publish 8000:8000 --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts,readonly comment-classifier-dev:0.1.0
docker inspect --format "{{.State.Health.Status}}" comment-classifier-api
docker logs comment-classifier-api
docker run --rm --network container:comment-classifier-api comment-classifier-dev:0.1.0 python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/health').json())"
docker stop comment-classifier-api
docker rm comment-classifier-api
```

修改发布镜像时，必须先从已验证的 Docker 卷导出模型，再验证构建和容器内推理：

```console
docker create --name comment-classifier-model-export --mount type=volume,source=comment-classifier-artifacts,target=/source comment-classifier-dev:0.1.0
docker cp comment-classifier-model-export:/source/model/. ./artifacts/model
docker rm comment-classifier-model-export
docker build --file Dockerfile.release --tag comment-classifier:review .
docker run --rm comment-classifier:review python -c "from comment_classifier.runtime import Predictor; print(Predictor().predict('客服一直不处理退款'))"
```

## 数据与模型要求

- 标签必须保持为 `positive`、`negative`、`neutral` 和 `complaint`，除非先同步修改完整流程与验收标准。
- 不要提交个人信息、客户数据或来源不明的数据。
- 不要提交基础模型缓存、训练模型或本地评估产物。
- 新增数据时必须保持训练集、验证集和测试集严格、确定性隔离。
- 训练和服务必须使用同一训练产物中保存的 tokenizer。
- 直接依赖版本、Python 基础镜像和基础模型 revision 的改变必须记录到 `docs/DECISIONS.md`。

## 文档要求

- 用户运行示例只能使用标准、单行 Docker CLI 或 Kubernetes 命令。
- 不得假设用户的操作系统、终端、宿主机 Python、curl 或绝对路径。
- 本地步骤只依赖 Docker Engine 或 Docker Desktop，不依赖额外编排工具。
- 已验证和未验证内容必须分开说明；Docker 本地通过不能写成 Kubernetes 或生产验收通过。
- Kubernetes 变化必须同步更新 `docs/KUBERNETES.md` 和 `deploy/kubernetes.yaml`。

## Pull Request 说明

Pull Request 应列出修改范围、实际执行的 Docker 验证命令、镜像标签或摘要、尚未验证的阶段以及已知限制。

提交到本项目并被接受的代码、文档和合成数据按项目根目录的 [MIT License](LICENSE) 发布。
