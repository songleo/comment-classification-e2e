# 中文电商评论分类：Docker 端到端项目

本项目用固定的四分类合成数据演示完整工程链路：数据校验、Transformer 微调、独立测试集评估、命令行推理、FastAPI 服务、发布镜像和 Kubernetes 部署。

项目只支持 Docker 交付。宿主机不需要安装 Python，也不提供宿主机虚拟环境、直接运行 Python 或直接启动 API 的操作步骤。

## 固定边界

- 标签固定为 `positive`、`negative`、`neutral` 和 `complaint`。
- 基础模型固定为 `hfl/rbt3` 的提交 `0412ffdc25bf738c556d523f8553bd69efe6405b`。
- 容器基础镜像固定为 Python 3.13.15 的 slim 变体，默认通过 DaoCloud Docker Hub 代理拉取；项目元数据要求 Python `>=3.13.15,<3.14`。
- Docker 默认从阿里云 PyTorch CPU 镜像安装 `torch 2.8.0+cpu`；当前交付不包含 CUDA 运行时。
- 数据是合成演示数据，不包含个人信息，测试结果不能代表生产准确率。
- Docker 本地验证、镜像仓库发布和 Kubernetes 部署是三个独立阶段；没有对应证据时不得互相替代。

## 文档导航

- [零基础 Docker 教程](docs/BEGINNER_GUIDE.md)
- [Docker 验证记录](docs/VALIDATION.md)
- [技术选择与限制](docs/DECISIONS.md)
- [Kubernetes 部署](docs/KUBERNETES.md)
- [贡献指南](CONTRIBUTING.md)
- [安全策略](SECURITY.md)

## 前置条件

宿主机只需要：

- Git；
- Docker Engine 或 Docker Desktop；
- Docker Compose 插件；
- 首次构建和首次训练时可访问镜像仓库、Python 包索引和 Hugging Face；
- 建议至少 4 GB 可用磁盘和 4 GB 可用内存。

确认 Docker 可用：

```powershell
docker version
docker compose version
```

## 两种验证方式

### 方式 A：本地构建并跑完整流程

适合开发者、审查者和需要重新训练的人。该方式会从源码构建开发镜像，真实执行测试、训练、评估、推理和 API 验证，并可以继续构建发布镜像。

### 方式 B：直接拉取已发布镜像

适合只想验证 API 的使用者。远端标签发布成功后，发布镜像已经包含通过验收的模型，不会在启动时下载基础模型或重新训练：

```powershell
docker pull songleo/comment-classification-e2e:0.1.0
docker run -d --name comment-classifier -p 8000:8000 songleo/comment-classification-e2e:0.1.0
docker inspect --format='{{json .State.Health}}' comment-classifier
```

Docker Hub 下载较慢时，可以通过 DaoCloud 代理拉取同一仓库镜像：

```powershell
docker pull docker.m.daocloud.io/songleo/comment-classification-e2e:0.1.0
docker tag docker.m.daocloud.io/songleo/comment-classification-e2e:0.1.0 songleo/comment-classification-e2e:0.1.0
```

验证结束后：

```powershell
docker stop comment-classifier
docker rm comment-classifier
```

直接拉取只能验证已发布镜像的 API 行为；不能替代源码测试、重新训练或本地发布镜像构建证据。

## 本地构建快速开始

### 1. 克隆项目

```powershell
git clone https://github.com/songleo/comment-classification-e2e.git
Set-Location comment-classification-e2e
```

### 2. 构建开发与训练镜像

```powershell
docker compose build
```

项目默认使用 DaoCloud 和阿里云国内镜像。需要切换来源时，可以在不改变版本的前提下覆盖构建参数：

```powershell
docker compose build `
  --build-arg PYTHON_IMAGE=python:3.13.15-slim `
  --build-arg PIP_INDEX_URL=https://pypi.org/simple `
  --build-arg TORCH_FIND_LINKS=https://download.pytorch.org/whl/cpu
```

### 3. 运行完整端到端验证

```powershell
docker compose run --rm e2e
```

该命令在容器内按顺序执行代码规范检查、单元测试、数据校验、真实训练、测试集评估和中文文本推理。模型与报告通过绑定目录保存到宿主机的 `artifacts/`，Hugging Face 基础模型缓存保存在 Docker 命名卷中。

如果 Hugging Face 官方站点访问缓慢，可以只为本次容器指定镜像端点：

```powershell
docker compose run --rm -e HF_ENDPOINT=https://hf-mirror.com e2e
```

只有命令以退出码 `0` 结束，才表示本地 Docker 端到端流程通过。

### 4. 启动 API

必须先完成端到端训练，确保 `artifacts/model/` 已生成：

```powershell
docker compose up -d api
docker compose ps
```

使用临时 curl 容器验证健康检查和中文预测，不依赖宿主机 curl：

```powershell
docker run --rm --network comment-classification-e2e_default curlimages/curl:8.10.1 -fsS http://api:8000/health

docker run --rm --network comment-classification-e2e_default curlimages/curl:8.10.1 `
  -fsS -X POST http://api:8000/predict `
  -H "Content-Type: application/json; charset=utf-8" `
  --data-raw '{"text":"客服一直不处理退款"}'
```

停止本地服务：

```powershell
docker compose down
```

`docker compose down` 不删除 Hugging Face 缓存卷。只有明确需要重新下载全部基础模型文件时，才执行 `docker compose down -v`。

## 分阶段运行

所有阶段仍通过 Docker 执行：

```powershell
docker compose run --rm e2e python -m ruff check .
docker compose run --rm e2e python -m pytest -q
docker compose run --rm e2e python -m comment_classifier.data_validation
docker compose run --rm e2e python -m comment_classifier.train
docker compose run --rm e2e python -m comment_classifier.evaluate
docker compose run --rm e2e python -m comment_classifier.predict --text "客服一直不处理退款"
```

训练和服务读取同一个 `artifacts/model/` 目录，其中同时保存模型、tokenizer 和训练元数据。

## 构建发布镜像

开发镜像包含测试、训练数据和开发工具；交付到镜像仓库或 Kubernetes 时，应在端到端训练通过后构建发布镜像。`Dockerfile.release` 从已经验证的本地开发镜像复制运行环境，不会再次下载 PyTorch，并移除测试命令：

```powershell
docker build -f Dockerfile.release -t songleo/comment-classification-e2e:0.1.0 .
docker run -d --name comment-classifier-release -p 8000:8000 songleo/comment-classification-e2e:0.1.0
docker inspect --format='{{json .State.Health}}' comment-classifier-release
```

发布镜像构建会检查模型关键文件是否存在，镜像只运行 API，不在启动时训练。需要发布到 Kubernetes 时，请继续阅读 [Kubernetes 部署文档](docs/KUBERNETES.md)。

## 生成物

| 路径 | 内容 |
| --- | --- |
| `artifacts/model/` | 微调模型、同一 tokenizer、训练元数据 |
| `artifacts/reports/test_metrics.json` | 机器可读测试指标 |
| `artifacts/reports/test_predictions.csv` | 每条测试样本的预测结果 |
| `artifacts/reports/test_report.md` | 人工可读评估报告 |

这些文件是本地生成物，不提交到 Git。发布镜像通过 `Dockerfile.release` 显式打包已经验证的 `artifacts/model/`。

## 当前验证边界

最新实测证据见 [docs/VALIDATION.md](docs/VALIDATION.md)。本地 Docker 通过不代表镜像已推送，也不代表 Kubernetes、生产网络、TLS、认证、容量或监控已经验收。

## 许可证

项目代码、文档和合成数据采用 [MIT License](LICENSE)。基础模型和第三方依赖继续适用各自许可证。
