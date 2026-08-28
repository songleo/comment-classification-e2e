# 贡献指南

感谢你改进这个中文评论分类端到端示例。项目优先接受能够保持流程可复现、适合公开分享，
并且不会夸大验证结论的贡献。

## 开始开发

1. Fork 本仓库，或在获得写入权限后创建功能分支。
2. 克隆你的仓库并进入仓库根目录：

   ```powershell
   git clone https://github.com/<your-account>/comment-classification-e2e.git
   Set-Location comment-classification-e2e
   ```

3. 创建虚拟环境并安装开发依赖：

   ```powershell
   python -m venv .venv
   $python = (Resolve-Path '.\.venv\Scripts\python.exe').Path
   & $python -m pip install --upgrade pip
   & $python -m pip install -e ".[dev]"
   ```

## 提交前检查

从仓库根目录运行：

```powershell
$python = (Resolve-Path '.\.venv\Scripts\python.exe').Path
& $python -m ruff check .
& $python -m pytest
& $python -m comment_classifier.data_validation
```

修改训练、评估或推理逻辑时，还应完成：

```powershell
& $python -m comment_classifier.train
& $python -m comment_classifier.evaluate
& $python -m comment_classifier.predict --text "客服一直不处理退款"
```

## 数据和模型要求

- 标签必须保持为 `positive`、`negative`、`neutral` 和 `complaint`，除非先讨论并同步修改完整流程。
- 不要提交个人信息、客户数据或来源不明的数据。
- 不要提交 `.venv/`、基础模型缓存、`artifacts/model/` 或本地生成的评估产物。
- 新增数据时必须保持训练集、验证集和测试集严格隔离。
- 训练与服务必须使用同一训练产物中保存的 tokenizer。

## 文档要求

- 一般说明优先使用中文，代码、接口字段和必须保持原样的技术名称除外。
- 不要写入本机用户名、盘符、工作区绝对路径、访问令牌或其他个人环境信息。
- 操作步骤应从仓库根目录出发，使用相对路径，并标明已经验证的平台和未验证边界。
- 不要把合成小数据集的结果描述成生产准确率或 Kubernetes 验收结果。

## Pull Request 建议

请在 Pull Request 中说明：

- 修改目的和范围；
- 执行过的验证命令及结果；
- 是否改变数据、模型配置、接口或部署方式；
- 尚未验证的内容和已知限制。
