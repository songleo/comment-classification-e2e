# 项目工作规则

## 项目目标

构建一个可复现的中文电商评论分类项目，完整覆盖数据集校验、Transformer 微调、评估、推理、API 服务和部署打包。

## 范围与边界

- 分类标签固定为 `positive`、`negative`、`neutral` 和 `complaint`。
- 项目内的数据是合成演示数据，不包含个人信息。
- 默认基础模型为 `hfl/rbt3`，具体模型版本固定在 `configs/train.json`。
- 没有真实部署证据时，不得声称已经通过生产环境或 Kubernetes 验证。
- 不得提交下载的基础模型缓存、虚拟环境或训练生成的模型产物。

## 必须执行的验证

从项目根目录运行：

```powershell
python -m pytest
python -m comment_classifier.data_validation
python -m comment_classifier.train
python -m comment_classifier.evaluate
python -m comment_classifier.predict --text "客服一直不处理退款"
```

完成标准：测试通过；训练集、验证集和测试集全部通过校验；训练能够生成可重新加载的模型；测试评估能够生成机器可读和人工可读的报告；`/predict` 使用同一个模型产物并能正常返回结果。

## 项目约定

- 一般说明文档默认先用中文编写；代码、命令、路径、接口字段、标识符以及必须保持原样的技术名称除外。
- 使用 Python 3.11 或更高版本、UTF-8 文件；公共函数应提供类型标注。
- 严格、确定性地隔离训练集、验证集和测试集。
- 训练和服务必须使用训练产物中保存的同一个 tokenizer。
- 重要技术选择和限制记录在 `docs/DECISIONS.md`。
