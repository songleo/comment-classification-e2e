# 贡献指南

本项目只接受可通过 Docker 复现的交付流程。贡献者不需要在宿主机安装 Python，文档、测试、训练、评估和 API 验证均以容器命令为准。

## 开始开发

```powershell
git clone https://github.com/<your-account>/comment-classification-e2e.git
Set-Location comment-classification-e2e
docker compose build
```

## 提交前验证

每次提交都必须从仓库根目录运行：

```powershell
docker compose run --rm e2e
```

修改 API、容器或部署文件时，还必须启动服务并检查容器健康状态：

```powershell
docker compose up -d api
docker compose ps
docker compose logs --no-color api
docker compose down
```

修改发布镜像时，必须在训练产物已经生成后验证构建：

```powershell
docker build -f Dockerfile.release -t comment-classifier:review .
```

## 数据与模型要求

- 标签必须保持为 `positive`、`negative`、`neutral` 和 `complaint`，除非先同步修改完整流程与验收标准。
- 不要提交个人信息、客户数据或来源不明的数据。
- 不要提交基础模型缓存、训练模型或本地评估产物。
- 新增数据时必须保持训练集、验证集和测试集严格、确定性隔离。
- 训练和服务必须使用同一训练产物中保存的 tokenizer。
- 直接依赖版本、Python 基础镜像和基础模型 revision 的改变必须记录到 `docs/DECISIONS.md`。

## 文档要求

- 所有用户运行示例必须以 `docker`、`docker compose` 或 Kubernetes 容器部署命令开始，不提供宿主机 Python 运行步骤。
- 公开文档不得写入用户名、盘符、工作区绝对路径、访问令牌或私有仓库地址。
- 已验证和未验证内容必须分开说明；Docker 本地通过不能写成 Kubernetes 或生产验收通过。
- Kubernetes 变化必须同步更新 `docs/KUBERNETES.md` 和 `deploy/kubernetes.yaml`。

## Pull Request 说明

Pull Request 应列出修改范围、实际执行的 Docker 验证命令、镜像标签或摘要、尚未验证的阶段以及已知限制。

提交到本项目并被接受的代码、文档和合成数据按项目根目录的 [MIT License](LICENSE) 发布。
