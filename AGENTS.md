# 项目工作规则

## 项目目标

构建一个可复现的中文电商评论分类项目，通过 Docker 完整覆盖数据集校验、Transformer 微调、评估、推理、API 服务、发布镜像和 Kubernetes 部署资料。

## 范围与边界

- 分类标签固定为 `positive`、`negative`、`neutral` 和 `complaint`。
- 项目数据是合成演示数据，不包含个人信息。
- 基础模型与 revision 固定在 `configs/train.json`。
- 唯一支持的交付和运行方式是 Docker；不得新增宿主机 Python、虚拟环境或直接运行 API 的文档路径。
- 开发与训练容器固定使用 `python:3.13.15-slim`，项目 Python 约束为 `>=3.13.15,<3.14`。
- 当前容器交付固定使用 PyTorch 2.8.0 CPU 轮子；GPU/CUDA 不在默认范围内。
- 没有真实证据时，不得声称已经完成镜像仓库、生产环境或 Kubernetes 验证。
- 不得提交基础模型缓存、训练模型、虚拟环境或本地评估产物。

## 必须执行的验证

从项目根目录运行：

```powershell
docker compose build
docker compose run --rm e2e
docker compose up -d api
docker compose ps
docker compose logs --no-color api
docker compose down
docker build -f Dockerfile.release -t comment-classifier:validation .
```

完成标准：容器镜像构建成功；代码规范检查和测试通过；三个数据集通过校验；训练生成可重新加载的模型与 tokenizer；评估生成机器可读和人工可读报告；CLI 推理成功；API 容器健康；发布镜像可以从同一模型产物构建。

Kubernetes 只允许先做客户端或服务端 dry-run；没有获批集群和镜像仓库时，不得实际发布，也不得记录为已验证。

## 项目约定

- 一般说明文档默认使用中文；代码、命令、路径、接口字段和技术名称除外。
- 公开文档不得包含维护者本机的用户名、盘符、绝对工作区路径或终端提示符。
- 所有用户示例必须通过 Docker 或 Kubernetes 运行容器，不得要求宿主机 Python。
- 使用 UTF-8；公共函数应提供类型标注。
- 严格、确定性地隔离训练集、验证集和测试集。
- 训练和服务必须使用训练产物中保存的同一个 tokenizer。
- 重要技术选择和限制记录在 `docs/DECISIONS.md`。
