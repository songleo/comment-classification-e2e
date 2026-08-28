# 零基础 Docker 教程

这份教程只讲容器方式。宿主机负责运行 Docker，Python、PyTorch、Transformers、FastAPI、测试工具和训练代码都在镜像内运行。

## 1. 先理解两个镜像

项目把开发训练与最终交付分开：

| 镜像 | 构建文件 | 包含内容 | 用途 |
| --- | --- | --- | --- |
| 开发与训练镜像 | `Dockerfile` | 源码、数据、配置、测试和开发依赖 | 测试、训练、评估、推理、本地 API |
| 发布镜像 | `Dockerfile.release` | API 运行依赖和已经训练好的模型 | 镜像仓库、Kubernetes、交付 |

两者都固定使用 Python 3.13.15 slim 镜像。宿主机 Python 的版本、包和配置不会进入容器，也不会影响训练结果。Dockerfile 默认通过 DaoCloud 拉取基础镜像，并从阿里云 PyTorch CPU 镜像安装 `torch 2.8.0+cpu`，避免把未使用的 CUDA 运行时打入镜像。

## 2. 两种使用方式

需要审查源码、重新训练或生成自己的模型时，使用 `docker compose build` 和 `docker compose run --rm e2e` 完成本地构建。

Docker Hub 标签发布成功后，只验证已经发布的 API 时，可以直接拉取包含模型的发布镜像：

```powershell
docker pull songleo/comment-classification-e2e:0.1.0
docker run -d --name comment-classifier -p 8000:8000 songleo/comment-classification-e2e:0.1.0
docker inspect --format='{{json .State.Health}}' comment-classifier
```

Docker Hub 较慢时使用 DaoCloud 代理：

```powershell
docker pull docker.m.daocloud.io/songleo/comment-classification-e2e:0.1.0
docker tag docker.m.daocloud.io/songleo/comment-classification-e2e:0.1.0 songleo/comment-classification-e2e:0.1.0
```

直接拉取只验证已发布 API；后续章节的本地构建路径还会验证源码、数据和训练。

## 3. 数据如何流动

完整流程如下：

```text
Docker 构建开发镜像
        ↓
容器校验 train / validation / test
        ↓
容器下载固定 revision 的 hfl/rbt3
        ↓
容器微调并选择验证集最佳模型
        ↓
模型和 tokenizer 写入 artifacts/model
        ↓
容器加载保存后的模型评估和推理
        ↓
Compose API 挂载同一个 artifacts/model
        ↓
Dockerfile.release 把同一个模型打入发布镜像
```

`artifacts/` 是绑定到容器的宿主机目录，因此临时训练容器退出后，模型和报告仍然存在。基础模型缓存位于 Docker 命名卷，避免每次重新下载。

## 4. 构建镜像

在仓库根目录执行：

```powershell
docker compose build
```

构建过程默认通过国内镜像安装 `pyproject.toml` 中锁定的直接依赖和 CPU 版 PyTorch。需要回到官方源时可以显式覆盖：

```powershell
docker compose build `
  --build-arg PYTHON_IMAGE=python:3.13.15-slim `
  --build-arg PIP_INDEX_URL=https://pypi.org/simple `
  --build-arg TORCH_FIND_LINKS=https://download.pytorch.org/whl/cpu
```

镜像只改变下载来源，不改变 `torch==2.8.0`、`transformers==4.55.2` 等直接依赖版本。

## 5. 一条命令跑完整流程

```powershell
docker compose run --rm e2e
```

容器内依次执行：

1. Ruff 代码规范检查；
2. Pytest 单元测试；
3. 三个数据集的格式、标签数量和跨集合重复检查；
4. 固定基础模型 revision 的真实微调；
5. 独立测试集评估；
6. 保存后模型的中文推理。

`--rm` 表示命令结束后删除这次临时容器，不会删除镜像、`artifacts/` 或 Hugging Face 缓存卷。

首次训练需要下载基础模型。官方端点较慢时，可以为本次容器指定镜像：

```powershell
docker compose run --rm -e HF_ENDPOINT=https://hf-mirror.com e2e
```

## 6. 分阶段观察

初学者可以逐步执行，每一步仍然只在容器中运行：

```powershell
docker compose run --rm e2e python -m pytest -q
docker compose run --rm e2e python -m comment_classifier.data_validation
docker compose run --rm e2e python -m comment_classifier.train
docker compose run --rm e2e python -m comment_classifier.evaluate
docker compose run --rm e2e python -m comment_classifier.predict --text "客服一直不处理退款"
```

训练命令生成 `artifacts/model/`。评估和推理命令只加载该目录，不重新选择 tokenizer 或基础模型。

## 7. 四个标签

| 标签 | 判断重点 | 示例 |
| --- | --- | --- |
| `positive` | 明确满意、称赞或问题已妥善解决 | 物流很快，包装也很仔细 |
| `negative` | 明确不满，但没有要求平台介入 | 更新后软件经常闪退 |
| `neutral` | 客观描述，没有明显情绪或处理要求 | 今天收到商品，暂时还没使用 |
| `complaint` | 要求退款、维权、升级或客服介入 | 客服一直不处理退款申请 |

如果一句话既有负面情绪，又明确要求介入，应标记为 `complaint`。

## 8. 训练参数

`configs/train.json` 固定基础模型、revision、随机种子、最大长度、批大小、学习率、训练轮数和投诉召回率门槛。固定 revision 能避免上游模型仓库变化导致同一项目下载不同文件。

训练每轮会输出 loss 和宏平均 F1。项目根据验证集宏平均 F1 保存最佳模型，不保证最后一轮就是最佳模型。

## 9. 评估结果

评估输出包括：

- Accuracy：全部测试样本中预测正确的比例；
- Macro F1：四个类别 F1 的等权平均；
- Complaint recall：真实投诉中被识别出来的比例；
- Confusion matrix：各真实标签被预测到哪个标签。

投诉召回率门槛为 `0.70`。即使门槛通过，也只说明当前合成测试集通过，不能外推到真实生产数据。

## 10. 启动和验证 API

训练通过后启动：

```powershell
docker compose up -d api
docker compose ps
```

Compose 网络内的服务名是 `api`。使用一次性 curl 容器调用接口：

```powershell
docker run --rm --network comment-classification-e2e_default curlimages/curl:8.10.1 -fsS http://api:8000/health

docker run --rm --network comment-classification-e2e_default curlimages/curl:8.10.1 `
  -fsS -X POST http://api:8000/predict `
  -H "Content-Type: application/json; charset=utf-8" `
  --data-raw '{"text":"物流很快，商品也很好用"}'
```

接口文档位于 `http://127.0.0.1:8000/docs`。停止服务：

```powershell
docker compose down
```

## 11. 发布镜像

发布镜像不会在启动时训练。必须先确认端到端命令通过、开发镜像仍在本机且 `artifacts/model/` 完整，再构建。发布构建复用开发镜像中的运行环境，不会再次下载 PyTorch：

```powershell
docker build -f Dockerfile.release -t songleo/comment-classification-e2e:0.1.0 .
docker run -d --name comment-classifier-release -p 8000:8000 songleo/comment-classification-e2e:0.1.0
docker logs comment-classifier-release
```

验证结束后：

```powershell
docker stop comment-classifier-release
docker rm comment-classifier-release
```

要发布到 Kubernetes，继续阅读 [Kubernetes 部署文档](KUBERNETES.md)。

## 12. 常见问题

### Docker 命令不存在

先安装并启动 Docker Desktop 或 Docker Engine，再确认：

```powershell
docker version
docker compose version
```

### 构建下载很慢

项目默认使用国内镜像。若曾覆盖为官方源，可显式恢复国内镜像并重新构建：

```powershell
docker compose build --no-cache `
  --build-arg PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.13.15-slim `
  --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ `
  --build-arg TORCH_FIND_LINKS=https://mirrors.aliyun.com/pytorch-wheels/cpu/
```

### 基础模型下载失败

先检查网络和证书，再按需要为单次训练容器设置 Hugging Face 端点：

```powershell
docker compose run --rm -e HF_ENDPOINT=https://hf-mirror.com e2e
```

### API 容器不健康

确认训练产物存在，然后查看容器状态与日志：

```powershell
docker compose ps
docker compose logs --no-color api
docker compose run --rm e2e python -m comment_classifier.predict --text "客服一直不处理退款"
```

### 磁盘空间不足

先查看 Docker 占用：

```powershell
docker system df
```

删除缓存卷会导致下次重新下载基础模型，因此只有确认不再需要缓存时才执行：

```powershell
docker compose down -v
```

## 13. 能证明什么

Docker 端到端通过可以证明当前代码、数据、依赖、训练、评估、推理和 API 在该容器环境中闭环。它不能证明真实业务准确率，也不能自动证明镜像仓库推送、Kubernetes、TLS、权限、容量、监控或生产回滚已经通过。
