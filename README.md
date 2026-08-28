# 中文评论分类：完整可运行的端到端流程

本项目把博客中的业务场景实现成可执行代码，完整覆盖：已标注数据 → 数据校验 → 中文预训练模型微调 → 验证集选模 → 独立测试集评估 → 命令行推理 → FastAPI 在线服务 → Docker/Kubernetes 部署打包。

项目面向学习、演示和工程验证。仓库提交的是源代码、配置和合成数据，不提交虚拟环境、
基础模型缓存或训练生成的模型文件。

## 文档导航

- [快速开始](#快速开始)
- [零基础教程](docs/BEGINNER_GUIDE.md)
- [参考验证记录](docs/VALIDATION.md)
- [技术选择与限制](docs/DECISIONS.md)
- [贡献指南](CONTRIBUTING.md)
- [安全问题报告](SECURITY.md)

## 项目中哪些内容是真实运行的

- 模型确实基于固定版本的中文预训练模型 `hfl/rbt3` 进行微调。
- 训练集、验证集和测试集是三个独立提交到项目中的文件。
- 测试报告由保存后的模型真实生成，不是写死的结果。
- API 加载训练时保存的同一套 tokenizer 和模型。
- 其他应用可以调用 `/health` 和 `/predict` 接口。

示例数据是有意控制规模的合成数据。它用于证明完整工程流程可以运行，不能代表生产环境中的业务准确率。

## 第一次阅读建议

如果你没有模型训练和推理经验，建议按下面顺序阅读：

1. [README.md](README.md)：先知道怎样运行项目。
2. [docs/BEGINNER_GUIDE.md](docs/BEGINNER_GUIDE.md)：理解训练流程、全部参数、指标和调试方法。
3. [docs/VALIDATION.md](docs/VALIDATION.md)：查看参考训练和测试结果是怎样计算出来的。
4. [docs/DECISIONS.md](docs/DECISIONS.md)：了解为什么选择当前模型、数据和验收指标。

## 分类标签

| 标签 | 含义 | 示例 |
| --- | --- | --- |
| `positive` | 明确满意或称赞 | 物流很快，包装也很仔细 |
| `negative` | 表达不满，但没有要求客服或平台介入 | 更新后软件经常闪退 |
| `neutral` | 陈述事实，没有明显情绪倾向 | 今天收到商品，暂时还没使用 |
| `complaint` | 要求介入、退款、维权或升级处理 | 客服一直不处理退款申请 |

如果一条评论既包含普通负面评价，又明确要求介入处理，应标记为 `complaint`。

## 快速开始

以下流程面向 Windows 10/11；参考验证环境为 Windows 11，并覆盖 Windows PowerShell 5.1
和 PowerShell 7。除非特别说明，后续命令都应从克隆后的仓库根目录执行，文档中的文件
路径也全部相对于仓库根目录。

### 第 1 步：准备 Windows 环境

不要直接从训练命令开始。必须先完成下面的环境准备，否则会遇到
“找不到 `python`”“没有 `.venv`”或“缺少依赖”等错误。

| 必备项 | 要求 | 用途 |
| --- | --- | --- |
| Windows | Windows 10 或 Windows 11，64 位 | 本文命令按本地 Windows 编写 |
| Git | 当前受支持的 Git for Windows | 克隆仓库和管理代码版本 |
| Python | 64 位 CPython 3.11、3.12 或 3.13 | 创建项目虚拟环境；不要把 Microsoft Store 的执行别名当成已安装 Python |
| PowerShell | Windows PowerShell 5.1 或 PowerShell 7 | 执行本文的 PowerShell 命令和项目脚本 |
| 网络 | 第一次安装依赖和下载基础模型时可访问 Python、PyPI 和 Hugging Face 资源 | 下载依赖及固定版本的 `hfl/rbt3`；缓存完成后可离线重复运行 |
| 磁盘和内存 | 建议至少保留 4 GB 磁盘空间、2 GB 内存 | 当前虚拟环境实测约 1.73 GiB，还需要模型缓存、训练产物和临时空间 |

CUDA 和独立显卡不是必需条件，本项目可以使用 CPU 完成训练。Docker 也不是本地
Python 验证的必需条件，只有测试容器部署路径时才需要安装。

### 先确认系统 Python 可用

从 [Python 官方 Windows 下载页](https://www.python.org/downloads/windows/) 获取受支持的
64 位安装程序，安装时应启用 `Add python.exe to PATH`。安装结束后，必须关闭安装前已经
打开的 CMD/PowerShell，再打开一个新的 PowerShell，然后执行：

```powershell
python --version
python -m pip --version
```

第一条命令必须显示 Python 3.11、3.12 或 3.13，第二条必须显示 pip 的版本和安装路径。
如果看到 `Python was not found`、跳转 Microsoft Store，或者提示 `python` 不是命令，说明
系统 Python 还没有准备好。请先安装受支持的 Python，并重新打开终端，不要继续执行训练命令。

`py --version` 可以作为补充检查，但 `py.exe` 不是所有 Windows 都有，因此本文不把它作为
唯一入口。

### 第 2 步：克隆仓库

先在终端中进入你希望保存源代码的目录，然后执行：

```powershell
git clone https://github.com/songleo/comment-classification-e2e.git
Set-Location comment-classification-e2e
Test-Path '.\pyproject.toml'
```

最后一条命令应返回 `True`，表示当前位于仓库根目录。不要在仓库外创建本项目的 `.venv`。

### 第 3 步：使用或创建虚拟环境

先检查项目中是否已经存在虚拟环境：

```powershell
Test-Path '.\.venv\Scripts\python.exe'
```

如果返回 `True`，直接复用它：

```powershell
$python = (Resolve-Path '.\.venv\Scripts\python.exe').Path
& $python --version
```

如果返回 `False`，先确认系统 Python 是否可用：

```powershell
python --version
```

应显示 Python 3.11、3.12 或 3.13。然后创建虚拟环境：

```powershell
python -m venv .venv
$python = (Resolve-Path '.\.venv\Scripts\python.exe').Path
```

如果提示 `python` 不是命令，请返回“开始前必须准备的 Windows 环境”，先完成 Python
安装和新终端检查。`py -3.12` 只有在 `py --version` 能成功运行时才可以作为替代命令，
不能假定所有 Windows 都有 `py.exe`。

后面的命令直接调用虚拟环境中的 Python，不需要执行激活脚本：

```powershell
& $python -m pip install --upgrade pip
& $python -m pip install -e ".[dev]"
& $python -m pip check
```

其中前两条 `pip install` 命令是在准备项目依赖，`pip check` 应输出
`No broken requirements found.`。只有依赖安装成功后，测试、训练、评估、推理和 API 命令
才具备运行条件。本文直接调用 `.venv\Scripts\python.exe`，不要求激活虚拟环境，也不受
PowerShell 激活脚本执行策略影响。

### 第 4 步：运行完整流程

首次完成环境初始化后，可以用下面的脚本依次执行测试、数据校验、训练、评估和命令行推理：

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

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/predict `
  -ContentType 'application/json; charset=utf-8' `
  -Body '{"text":"物流很快，商品也很好用"}'
```

`charset=utf-8` 不能省略：Windows PowerShell 5.1 发送不带字符集声明的中文
JSON 字符串时可能使用错误编码，导致服务收到乱码并给出错误分类。PowerShell 7 通常不会
复现这个问题，但这里保留显式声明，使同一条命令兼容两个版本。

也可以使用 Chrome 打开接口文档：

```text
http://127.0.0.1:8000/docs
```

生成的模型文件位于 `artifacts/model/`，评估结果位于 `artifacts/reports/`。两者都是本地构建产物，已通过 `.gitignore` 排除，不会提交到 Git。

## 手动执行各阶段

如果希望逐步观察每个阶段，而不是运行封装脚本，请在仓库根目录执行：

```powershell
$python = (Resolve-Path '.\.venv\Scripts\python.exe').Path
& $python -m pytest
& $python -m comment_classifier.data_validation
& $python -m comment_classifier.train
& $python -m comment_classifier.evaluate
& $python -m comment_classifier.predict --text "客服一直不处理退款"
```

每条命令成功后再执行下一条。各阶段含义、参数和输出解释见
[零基础教程](docs/BEGINNER_GUIDE.md)。

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
docs/VALIDATION.md               可复核的参考验证记录
docs/BEGINNER_GUIDE.md           零基础流程、参数、指标和调试详解
CONTRIBUTING.md                  贡献流程和提交前检查
SECURITY.md                      私下报告安全问题的方式
```

## 当前验证状态

- Windows 本地源码、数据、单元测试、CPU 真实训练、已保存模型评估、命令行推理和 FastAPI 服务：**已验证**，验证日期为 2026-08-28，详情见 [参考验证记录](docs/VALIDATION.md)。
- Docker 部署：参考验证范围未包含 Docker。`UNKNOWN` — 没有容器运行证据；验证方法：运行 `docker compose up --build`；负责人：运行环境维护人员；下一步：只有需要容器验证时才执行。
- Kubernetes 或公网部署：不在当前验收范围内。`UNKNOWN` — 当前未提供镜像仓库或集群；验证方法：在已批准集群中分阶段发布；负责人：部署负责人；下一步：除非扩大范围，否则无需执行。
- Linux、macOS：源代码按 Python 3.11–3.13 编写，但仓库中的便捷脚本是 PowerShell；当前没有完整平台验证证据，因此状态为 `UNKNOWN`。

## 贡献、安全与许可证

- 提交问题或代码前，请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。
- 安全漏洞不要发布到公开 Issue，请按 [SECURITY.md](SECURITY.md) 私下报告。
- 当前仓库尚未添加 `LICENSE`。公开可见不等于已经授予复制、修改或再分发权；许可证需要由仓库所有者 review 后明确选择。
