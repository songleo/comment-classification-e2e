# 中文评论分类：完整可运行的端到端流程

本项目把博客中的业务场景实现成可执行代码，完整覆盖：已标注数据 → 数据校验 → 中文预训练模型微调 → 验证集选模 → 独立测试集评估 → 命令行推理 → FastAPI 在线服务 → Docker/Kubernetes 部署打包。

## 项目中哪些内容是真实运行的

- 模型确实基于固定版本的中文预训练模型 `hfl/rbt3` 进行微调。
- 训练集、验证集和测试集是三个独立提交到项目中的文件。
- 测试报告由保存后的模型真实生成，不是写死的结果。
- API 加载训练时保存的同一套 tokenizer 和模型。
- 其他应用可以调用 `/health` 和 `/predict` 接口。

示例数据是有意控制规模的合成数据。它用于证明完整工程流程可以运行，不能代表生产环境中的业务准确率。

## 第一次阅读建议

如果你没有模型训练和推理经验，建议按下面顺序阅读：

1. `README.md`：先知道怎样运行项目。
2. `docs/BEGINNER_GUIDE.md`：理解训练流程、全部参数、指标和调试方法。
3. `docs/VALIDATION.md`：查看本次真实训练和测试结果是怎样计算出来的。
4. `docs/DECISIONS.md`：了解为什么选择当前模型、数据和验收指标。

## 分类标签

| 标签 | 含义 | 示例 |
| --- | --- | --- |
| `positive` | 明确满意或称赞 | 物流很快，包装也很仔细 |
| `negative` | 表达不满，但没有要求客服或平台介入 | 更新后软件经常闪退 |
| `neutral` | 陈述事实，没有明显情绪倾向 | 今天收到商品，暂时还没使用 |
| `complaint` | 要求介入、退款、维权或升级处理 | 客服一直不处理退款申请 |

如果一条评论既包含普通负面评价，又明确要求介入处理，应标记为 `complaint`。

## 运行条件

- Python 3.11–3.13
- 第一次训练时需要联网下载固定版本的基础模型
- 大约 1 GB 可用磁盘空间和 2 GB 内存；CUDA 可选
- 只有使用容器部署路径时才需要 Docker

## 在 Windows PowerShell 中运行完整流程

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
python -m comment_classifier.data_validation
python -m comment_classifier.train
python -m comment_classifier.evaluate
python -m comment_classifier.predict --text "客服一直不处理退款"
uvicorn comment_classifier.api:app --host 127.0.0.1 --port 8000
```

首次完成环境初始化后，可以用下面的命令重复执行从测试、训练到评估的完整流程：

```powershell
.\scripts\run-e2e.ps1
```

如果模型已经训练完成，可以直接启动本地服务：

```powershell
.\scripts\start-local-api.ps1
```

服务启动后，在第二个终端中验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict -ContentType 'application/json' -Body '{"text":"物流很快，商品也很好用"}'
```

也可以使用 Chrome 打开接口文档：

```text
http://127.0.0.1:8000/docs
```

生成的模型文件位于 `artifacts/model/`，评估结果位于 `artifacts/reports/`。两者都是本地构建产物，已通过 `.gitignore` 排除，不会提交到 Git。

## 容器部署

必须先完成训练，因为容器镜像会打包训练后保存的确切模型：

```powershell
docker compose up --build
```

如果使用 Kubernetes，需要先替换 `deploy/kubernetes.yaml` 中的镜像地址占位符，构建并推送不可变镜像，然后再在已批准的集群中应用清单。

## 项目结构

```text
configs/train.json               可复现的训练配置
data/{train,validation,test}.csv 固定的已标注数据集
src/comment_classifier/          数据校验、训练、评估、推理和 API
tests/                           数据与 API 契约测试
artifacts/                       生成的模型和评估报告
deploy/kubernetes.yaml           包含健康检查的部署模板
Dockerfile / compose.yaml        可部署的本地服务镜像
docs/DECISIONS.md                技术选择、风险和上线边界
docs/VALIDATION.md               本机真实验证记录
docs/BEGINNER_GUIDE.md           零基础流程、参数、指标和调试详解
```

## 当前验证状态

- 本地源码、数据、单元测试、CPU 真实训练、已保存模型评估、命令行推理和 FastAPI 部署：**已验证**，验证日期为 2026-08-28，详情见 `docs/VALIDATION.md`。
- Docker 部署：当前本机验收不要求。`UNKNOWN` — 当前主机未安装 Docker；验证方法：运行 `docker compose up --build`；负责人：运行环境维护人员；下一步：只有需要容器验证时才执行。
- Kubernetes 或公网部署：不在当前验收范围内。`UNKNOWN` — 当前未提供镜像仓库或集群；验证方法：在已批准集群中分阶段发布；负责人：部署负责人；下一步：除非扩大范围，否则无需执行。
