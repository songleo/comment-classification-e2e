# 中文电商评论分类：Docker 端到端项目

本项目用固定的四分类合成数据演示数据校验、Transformer 微调、独立测试集评估、命令行推理、FastAPI 服务、发布镜像和 Kubernetes 部署。

取得项目源码并进入项目根目录后，唯一运行前提是能够执行 `docker` 命令。Python、测试、训练、API 调用和文件复制全部在容器中完成。

## 固定边界

- 标签固定为 `positive`、`negative`、`neutral` 和 `complaint`。
- 基础模型固定为 `hfl/rbt3` 的提交 `0412ffdc25bf738c556d523f8553bd69efe6405b`。
- 容器基础镜像固定为 Python 3.13.15 slim，默认通过 DaoCloud Docker Hub 代理拉取。
- 默认从阿里云 PyTorch CPU 镜像安装 `torch 2.8.0+cpu`；当前交付不包含 CUDA 运行时。
- 数据是合成演示数据，不包含个人信息，测试结果不能代表生产准确率。
- 本地验证、镜像仓库发布和 Kubernetes 部署是三个独立阶段。

## 文档导航

- [零基础 Docker 教程](docs/BEGINNER_GUIDE.md)
- [项目博客材料](docs/BLOG_MATERIAL.md)
- [Docker 验证记录](docs/VALIDATION.md)
- [技术选择与限制](docs/DECISIONS.md)
- [Kubernetes 部署](docs/KUBERNETES.md)
- [贡献指南](CONTRIBUTING.md)
- [安全策略](SECURITY.md)

## 方式 A：从源码本地构建并验证

以下命令全部是单行标准 Docker CLI，逐条执行即可。

### 1. 确认 Docker

```console
docker version
```

### 2. 构建开发镜像

```console
docker build --tag comment-classifier-dev:0.1.0 .
```

默认构建已经使用国内镜像源。需要切换回官方源时：

```console
docker build --tag comment-classifier-dev:0.1.0 --build-arg PYTHON_IMAGE=python:3.13.15-slim --build-arg PIP_INDEX_URL=https://pypi.org/simple --build-arg TORCH_FIND_LINKS=https://download.pytorch.org/whl/cpu .
```

### 3. 创建持久化卷

模型、评估报告和基础模型缓存都由 Docker 管理，不绑定任何宿主机绝对路径：

```console
docker volume create comment-classifier-artifacts
docker volume create comment-classifier-huggingface-cache
```

这两个命令可以重复执行；已经存在的命名卷不会被清空。

### 4. 运行完整端到端验证

```console
docker run --rm --name comment-classifier-e2e --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts --mount type=volume,source=comment-classifier-huggingface-cache,target=/cache/huggingface --env HF_ENDPOINT=https://hf-mirror.com comment-classifier-dev:0.1.0 /bin/sh /app/scripts/run-e2e.sh
```

该容器依次执行 Ruff、Pytest、三个数据集校验、真实 CPU 训练、独立测试集评估和中文推理。退出码为 `0` 才表示通过。

### 5. 查找训练完成的模型

训练结果保存在 Docker 命名卷 `comment-classifier-artifacts` 中，不会因为端到端容器使用了 `--rm` 而被删除。模型在挂载该卷的容器内对应 `/app/artifacts/model/`。

只列出模型、tokenizer 和训练元数据文件：

```console
docker run --rm --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts,readonly comment-classifier-dev:0.1.0 python -c "from pathlib import Path; print('\n'.join(str(path) for path in sorted(Path('/app/artifacts/model').rglob('*')) if path.is_file()))"
```

此命令只读访问命名卷，不会复制或修改模型。需要把模型导出到项目目录时，继续执行第 8 步。

### 6. 启动 API

```console
docker run --detach --name comment-classifier-api --publish 8000:8000 --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts,readonly comment-classifier-dev:0.1.0
```

查看健康状态和日志：

```console
docker inspect --format "{{.State.Health.Status}}" comment-classifier-api
docker logs comment-classifier-api
```

刚启动时健康状态可能是 `starting`；等待片刻后再次执行 inspect，预期结果为 `healthy`。

### 7. 使用 Docker 容器验证 API

验证容器直接共享 API 容器的网络，不依赖宿主机 curl、端口回环名称或操作系统网络约定。

健康检查：

```console
docker run --rm --network container:comment-classifier-api comment-classifier-dev:0.1.0 python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/health').json())"
```

中文预测：

```console
docker run --rm --network container:comment-classifier-api comment-classifier-dev:0.1.0 python -c "import httpx; print(httpx.post('http://127.0.0.1:8000/predict', json={'text':'客服一直不处理退款'}).json())"
```

如需人工查看接口页面，可打开 `http://127.0.0.1:8000/docs`。

停止并删除 API 容器：

```console
docker stop comment-classifier-api
docker rm comment-classifier-api
```

### 8. 构建发布镜像

发布构建需要把命名卷中的已验证模型复制到仓库相对目录。整个导出过程仍由 Docker 完成：

```console
docker create --name comment-classifier-model-export --mount type=volume,source=comment-classifier-artifacts,target=/source comment-classifier-dev:0.1.0
docker cp comment-classifier-model-export:/source/model/. ./artifacts/model
docker rm comment-classifier-model-export
```

构建并验证发布镜像：

```console
docker build --file Dockerfile.release --tag songleo/comment-classification-e2e:0.1.0 .
docker run --detach --name comment-classifier-release --publish 8000:8000 songleo/comment-classification-e2e:0.1.0
docker inspect --format "{{.State.Health.Status}}" comment-classifier-release
docker logs comment-classifier-release
docker run --rm --network container:comment-classifier-release songleo/comment-classification-e2e:0.1.0 python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')))"
docker run --rm --network container:comment-classifier-release songleo/comment-classification-e2e:0.1.0 python -c "import json,urllib.request; request=urllib.request.Request('http://127.0.0.1:8000/predict',data=json.dumps({'text':'\u5ba2\u670d\u4e00\u76f4\u4e0d\u5904\u7406\u9000\u6b3e'}).encode(),headers={'Content-Type':'application/json'}); print(json.load(urllib.request.urlopen(request)))"
docker stop comment-classifier-release
docker rm comment-classifier-release
```

发布容器没有挂载模型卷。它能健康启动并预测，说明模型和同一 tokenizer 已经打入镜像。

## 方式 B：直接拉取发布镜像

已发布镜像的不可变摘要为 `sha256:a971d00cc98932d08be4de1f65e14fc3af9dcdd3f768079ce14e472495c10b22`。只验证 API 时不需要构建开发镜像或训练模型：

```console
docker pull songleo/comment-classification-e2e:0.1.0
docker run --detach --name comment-classifier --publish 8000:8000 songleo/comment-classification-e2e:0.1.0
docker inspect --format "{{.State.Health.Status}}" comment-classifier
docker logs comment-classifier
docker run --rm --network container:comment-classifier songleo/comment-classification-e2e:0.1.0 python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')))"
docker run --rm --network container:comment-classifier songleo/comment-classification-e2e:0.1.0 python -c "import json,urllib.request; request=urllib.request.Request('http://127.0.0.1:8000/predict',data=json.dumps({'text':'\u5ba2\u670d\u4e00\u76f4\u4e0d\u5904\u7406\u9000\u6b3e'}).encode(),headers={'Content-Type':'application/json'}); print(json.load(urllib.request.urlopen(request)))"
```

刚启动时可能显示 `starting`；等待片刻后重新执行 inspect，预期为 `healthy`。

Docker Hub 下载较慢或当前 Docker Hub 代理不支持该仓库时，使用已验证的国内加速入口，再标记为相同的标准镜像名：

```console
docker pull docker.1ms.run/songleo/comment-classification-e2e:0.1.0
docker tag docker.1ms.run/songleo/comment-classification-e2e:0.1.0 songleo/comment-classification-e2e:0.1.0
```

加速入口只改变下载地址，不改变镜像内容；本次实测两种地址得到相同镜像 ID。完成 pull 和 tag 后，继续执行上面的 run、inspect、logs、`/health` 和 `/predict` 命令。

验证结束后：

```console
docker stop comment-classifier
docker rm comment-classifier
```

完整实测记录见 [验证记录](docs/VALIDATION.md)。

## 单独运行某个阶段

命名卷 `comment-classifier-artifacts` 保存训练结果。以下示例仍只使用 Docker：

```console
docker run --rm --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts comment-classifier-dev:0.1.0 python -m pytest -q
docker run --rm --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts comment-classifier-dev:0.1.0 python -m comment_classifier.data_validation
docker run --rm --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts --mount type=volume,source=comment-classifier-huggingface-cache,target=/cache/huggingface --env HF_ENDPOINT=https://hf-mirror.com comment-classifier-dev:0.1.0 python -m comment_classifier.train
docker run --rm --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts comment-classifier-dev:0.1.0 python -m comment_classifier.evaluate
docker run --rm --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts,readonly comment-classifier-dev:0.1.0 python -m comment_classifier.predict --text "客服一直不处理退款"
```

## 清理本地测试资源

只有确认不再需要模型、报告和缓存时才执行：

```console
docker volume rm comment-classifier-artifacts
docker volume rm comment-classifier-huggingface-cache
docker image rm comment-classifier-dev:0.1.0
```

容器、镜像和命名卷是三个独立对象；删除临时容器不会删除镜像或卷。

## 当前验证边界

最新实测证据见 [docs/VALIDATION.md](docs/VALIDATION.md)。本地构建链路和已发布远端镜像均已验证；这不代表 Kubernetes 集群、生产网络、TLS、认证、容量或监控已经验收。

## 许可证

项目代码、文档和合成数据采用 [MIT License](LICENSE)。基础模型和第三方依赖继续适用各自许可证。
