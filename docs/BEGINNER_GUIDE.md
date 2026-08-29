# 零基础 Docker 教程

用户取得项目源码并进入项目根目录后，只要能够执行 `docker` 命令，就可以逐条完成所有步骤。Python、PyTorch、测试、训练、API 调用和模型导出都由 Docker 容器完成。

## 1. 确认 Docker

```console
docker version
```

如果该命令失败，应先修复 Docker 安装或启动状态。项目不要求宿主机 Python、curl 或额外的容器编排工具。

## 2. 理解两个镜像

| 镜像 | 构建文件 | 用途 |
| --- | --- | --- |
| `comment-classifier-dev:0.1.0` | `Dockerfile` | 测试、训练、评估、推理、本地 API |
| `songleo/comment-classification-e2e:0.1.0` | `Dockerfile.release` | 独立 API、镜像仓库、Kubernetes |

开发镜像不包含训练结果。训练结果先保存在 Docker 命名卷，再被复制进发布镜像。

## 3. 构建开发镜像

```console
docker build --tag comment-classifier-dev:0.1.0 .
```

构建成功后确认镜像存在：

```console
docker image inspect comment-classifier-dev:0.1.0
```

默认下载来源：

- Python 基础镜像：DaoCloud Docker Hub 代理；
- Python 包：阿里云 PyPI；
- PyTorch CPU 轮子：阿里云 PyTorch wheels。

需要临时改用官方源时：

```console
docker build --tag comment-classifier-dev:0.1.0 --build-arg PYTHON_IMAGE=python:3.13.15-slim --build-arg PIP_INDEX_URL=https://pypi.org/simple --build-arg TORCH_FIND_LINKS=https://download.pytorch.org/whl/cpu .
```

## 4. 创建 Docker 命名卷

```console
docker volume create comment-classifier-artifacts
docker volume create comment-classifier-huggingface-cache
```

用途：

- `comment-classifier-artifacts`：保存训练模型、同一 tokenizer 和评估报告；
- `comment-classifier-huggingface-cache`：保存基础模型下载缓存。

命名卷由 Docker 管理，不需要拼接宿主机路径，也不受操作系统路径格式影响。重复执行 create 不会清空已有内容。

## 5. 跑完整流程

```console
docker run --rm --name comment-classifier-e2e --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts --mount type=volume,source=comment-classifier-huggingface-cache,target=/cache/huggingface --env HF_ENDPOINT=https://hf-mirror.com comment-classifier-dev:0.1.0 /bin/sh /app/scripts/run-e2e.sh
```

该容器按顺序执行：

1. Ruff 代码规范检查；
2. Pytest 单元测试；
3. 训练、验证和测试数据校验；
4. 固定基础模型 revision 的真实 CPU 微调；
5. 独立测试集评估；
6. 保存后模型的中文推理。

`--rm` 只删除本次临时容器，不删除开发镜像或两个命名卷。命令退出码为 `0` 才算通过。

## 6. 查找训练完成的模型和报告

训练结果保存在 Docker 命名卷 `comment-classifier-artifacts` 中。端到端命令的 `--rm` 只删除临时容器，不会删除该卷。模型在挂载该卷的容器内对应 `/app/artifacts/model/`。

只列出训练完成的模型、tokenizer 和训练元数据文件：

```console
docker run --rm --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts,readonly comment-classifier-dev:0.1.0 python -c "from pathlib import Path; print('\n'.join(str(path) for path in sorted(Path('/app/artifacts/model').rglob('*')) if path.is_file()))"
```

查看模型和评估报告的全部文件：

```console
docker run --rm --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts,readonly comment-classifier-dev:0.1.0 python -c "from pathlib import Path; print('\n'.join(str(path) for path in sorted(Path('/app/artifacts').rglob('*')) if path.is_file()))"
```

这两个命令都只读访问命名卷，不会复制或修改文件。需要把模型复制到项目目录时，执行第 11 节的导出步骤。

主要内容：

| 容器内路径 | 内容 |
| --- | --- |
| `/app/artifacts/model/` | 模型、tokenizer、训练元数据 |
| `/app/artifacts/reports/test_metrics.json` | 测试指标 |
| `/app/artifacts/reports/test_predictions.csv` | 测试集逐条预测 |
| `/app/artifacts/reports/test_report.md` | 人工可读报告 |

## 7. 单独重跑测试或推理

单元测试：

```console
docker run --rm --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts comment-classifier-dev:0.1.0 python -m pytest -q
```

中文推理：

```console
docker run --rm --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts,readonly comment-classifier-dev:0.1.0 python -m comment_classifier.predict --text "客服一直不处理退款"
```

这里的 Python 是容器内命令，不是宿主机命令。

## 8. 启动 API

```console
docker run --detach --name comment-classifier-api --publish 8000:8000 --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts,readonly comment-classifier-dev:0.1.0
```

查询健康状态：

```console
docker inspect --format "{{.State.Health.Status}}" comment-classifier-api
```

刚启动时可能显示 `starting`。等待片刻后再次执行，预期结果为 `healthy`。如果没有变为健康：

```console
docker logs comment-classifier-api
```

## 9. 只用 Docker 调用 API

验证容器共享 API 容器的网络，因此不依赖宿主机 curl 或特殊主机名。

健康检查：

```console
docker run --rm --network container:comment-classifier-api comment-classifier-dev:0.1.0 python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/health').json())"
```

中文预测：

```console
docker run --rm --network container:comment-classifier-api comment-classifier-dev:0.1.0 python -c "import httpx; print(httpx.post('http://127.0.0.1:8000/predict', json={'text':'客服一直不处理退款'}).json())"
```

如果需要人工查看 OpenAPI 页面，可访问 `http://127.0.0.1:8000/docs`。

## 10. 停止 API

```console
docker stop comment-classifier-api
docker rm comment-classifier-api
```

停止和删除容器不会删除开发镜像或命名卷。

## 11. 导出模型并构建发布镜像

发布构建需要仓库相对目录 `./artifacts/model`。用一个不启动的临时容器读取命名卷，并让 Docker 执行复制：

```console
docker create --name comment-classifier-model-export --mount type=volume,source=comment-classifier-artifacts,target=/source comment-classifier-dev:0.1.0
docker cp comment-classifier-model-export:/source/model/. ./artifacts/model
docker rm comment-classifier-model-export
```

构建发布镜像：

```console
docker build --file Dockerfile.release --tag songleo/comment-classification-e2e:0.1.0 .
```

独立启动，不挂载模型卷：

```console
docker run --detach --name comment-classifier-release --publish 8000:8000 songleo/comment-classification-e2e:0.1.0
docker inspect --format "{{.State.Health.Status}}" comment-classifier-release
docker logs comment-classifier-release
docker run --rm --network container:comment-classifier-release songleo/comment-classification-e2e:0.1.0 python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')))"
docker run --rm --network container:comment-classifier-release songleo/comment-classification-e2e:0.1.0 python -c "import json,urllib.request; request=urllib.request.Request('http://127.0.0.1:8000/predict',data=json.dumps({'text':'\u5ba2\u670d\u4e00\u76f4\u4e0d\u5904\u7406\u9000\u6b3e'}).encode(),headers={'Content-Type':'application/json'}); print(json.load(urllib.request.urlopen(request)))"
docker stop comment-classifier-release
docker rm comment-classifier-release
```

发布容器能够独立预测，说明模型与 tokenizer 已经打入镜像。

## 12. 直接拉取发布镜像

远端镜像已经发布，摘要为 `sha256:a971d00cc98932d08be4de1f65e14fc3af9dcdd3f768079ce14e472495c10b22`。可以跳过源码训练：

```console
docker pull songleo/comment-classification-e2e:0.1.0
docker run --detach --name comment-classifier --publish 8000:8000 songleo/comment-classification-e2e:0.1.0
docker inspect --format "{{.State.Health.Status}}" comment-classifier
docker logs comment-classifier
docker run --rm --network container:comment-classifier songleo/comment-classification-e2e:0.1.0 python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')))"
docker run --rm --network container:comment-classifier songleo/comment-classification-e2e:0.1.0 python -c "import json,urllib.request; request=urllib.request.Request('http://127.0.0.1:8000/predict',data=json.dumps({'text':'\u5ba2\u670d\u4e00\u76f4\u4e0d\u5904\u7406\u9000\u6b3e'}).encode(),headers={'Content-Type':'application/json'}); print(json.load(urllib.request.urlopen(request)))"
docker stop comment-classifier
docker rm comment-classifier
```

刚启动时可能显示 `starting`；等待片刻后再次执行 inspect。预期健康检查返回 `ok`，预测标签返回 `complaint`。

Docker Hub 下载较慢或当前 Docker Hub 代理不支持该仓库时：

```console
docker pull docker.1ms.run/songleo/comment-classification-e2e:0.1.0
docker tag docker.1ms.run/songleo/comment-classification-e2e:0.1.0 songleo/comment-classification-e2e:0.1.0
```

本次实测该加速地址与 Docker Hub 地址得到相同镜像 ID。完成 pull 和 tag 后，再执行本节的 run 与接口验证命令。

## 13. 常见问题

### 容器名称已被占用

查看项目相关容器：

```console
docker ps --all --filter name=comment-classifier
```

确认旧测试容器不再需要后，按名称停止并删除。

Docker 报错中出现哪个名称，就只清理对应的旧测试容器：

```console
docker rm --force comment-classifier-e2e
docker rm --force comment-classifier-api
docker rm --force comment-classifier-model-export
docker rm --force comment-classifier-release
docker rm --force comment-classifier
docker rm --force comment-classifier-manifest-check
docker rm --force comment-classifier-kubernetes-input-copy
```

不要删除与报错无关的容器，也不要用全局清理命令代替按名称处理。

### API 不健康

```console
docker inspect --format "{{json .State.Health}}" comment-classifier-api
docker logs comment-classifier-api
docker run --rm --mount type=volume,source=comment-classifier-artifacts,target=/app/artifacts,readonly comment-classifier-dev:0.1.0 python -m comment_classifier.predict --text "客服一直不处理退款"
```

### 下载很慢

默认 Dockerfile 已配置国内基础镜像和 Python 包源，完整验证命令也配置了 `hf-mirror.com`。如果曾覆盖为官方源，重新使用第 3 节的默认构建命令。

### 磁盘空间不足

```console
docker system df
```

只有明确不再需要模型和缓存时才删除卷：

```console
docker volume rm comment-classifier-artifacts
docker volume rm comment-classifier-huggingface-cache
```

## 14. 验证边界

本地 Docker 端到端通过可以证明当前代码、数据、依赖、训练、评估、推理和 API 在该容器环境中闭环；远端镜像拉取与接口验证也已单独通过。两者都不能证明真实业务准确率，也不能自动证明 Kubernetes 集群、TLS、权限、容量、监控或生产回滚已经通过。
