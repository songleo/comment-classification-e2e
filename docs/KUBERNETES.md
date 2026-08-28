# Kubernetes 部署

本文只部署已经训练并验证的发布镜像。Kubernetes Pod 不负责训练，也不从 Hugging Face 下载基础模型。所有命令都是标准、单行 Docker 或 kubectl CLI，不假设操作系统或终端。

## 1. 前置条件

- 开发镜像已经通过直接 `docker run` 端到端验证；
- Docker 命名卷 `comment-classifier-artifacts` 中存在模型、tokenizer 和 `training_metadata.json`；
- `Dockerfile.release` 已成功构建并独立运行；
- 目标节点能够运行当前 CPU-only PyTorch 镜像；
- Docker Hub 目标仓库 `songleo/comment-classification-e2e` 可写；
- 有获批的 Kubernetes 集群与 `kubectl` 访问权限；
- 部署方已经决定镜像拉取凭据、命名空间、TLS、认证、网络策略、监控和回滚要求。

没有镜像仓库或获批集群时，只能审查文件和执行客户端 dry-run，不能声称部署通过。

## 2. 从 Docker 卷导出模型

```console
docker create --name comment-classifier-model-export --mount type=volume,source=comment-classifier-artifacts,target=/source comment-classifier-dev:0.1.0
docker cp comment-classifier-model-export:/source/model/. ./artifacts/model
docker rm comment-classifier-model-export
```

## 3. 构建发布镜像

```console
docker build --file Dockerfile.release --tag songleo/comment-classification-e2e:0.1.0 .
docker run --rm songleo/comment-classification-e2e:0.1.0 python -c "from comment_classifier.runtime import Predictor; print(Predictor().predict('客服一直不处理退款'))"
```

第二条命令在发布容器内重新加载已经打包的模型和 tokenizer，并执行一次推理。

## 4. 推送并记录摘要

```console
docker push songleo/comment-classification-e2e:0.1.0
docker inspect --format "{{json .RepoDigests}}" songleo/comment-classification-e2e:0.1.0
```

把实际仓库返回的不可变摘要记录到发布证据中。正式部署优先使用 `docker.io/songleo/comment-classification-e2e@sha256:<digest>`，不要只记录可变标签。

## 5. 修改部署清单

编辑 `deploy/kubernetes.yaml`，把示例镜像替换为实际的不可变摘要。若仓库需要认证，应由集群管理员按组织规范创建 `imagePullSecret`，不要把明文用户名、密码或令牌写入仓库。

默认清单包含：

- 1 个副本的 Deployment；
- `/health` readiness 和 liveness 探针；
- CPU、内存 requests 和 limits；
- 非 root、只读根文件系统和禁用权限提升；
- ClusterIP Service，仅在集群内暴露 80 端口。

## 6. 部署前校验

先做客户端语法校验：

```console
kubectl apply --dry-run=client -f deploy/kubernetes.yaml
```

有获批集群时，再做服务端校验：

```console
kubectl apply --dry-run=server -f deploy/kubernetes.yaml
```

服务端 dry-run 会验证集群 API、准入策略和当前资源定义，但不会创建工作负载。

## 7. 发布与观察

只有变更窗口和审批齐全时执行：

```console
kubectl apply -f deploy/kubernetes.yaml
kubectl rollout status deployment/comment-classifier --timeout=5m
kubectl get pods -l app=comment-classifier -o wide
kubectl get service comment-classifier
kubectl get events --sort-by=.lastTimestamp
```

如果 rollout 失败，先读取 Pod 描述和日志：

```console
kubectl describe pods -l app=comment-classifier
kubectl logs deployment/comment-classifier --all-containers=true --tail=200
```

## 8. 集群内验收

```console
kubectl run comment-classifier-smoke --image=curlimages/curl:8.10.1 --restart=Never --rm -i --command -- curl -fsS http://comment-classifier/health
```

预测验收应至少覆盖四个标签、空字符串校验、超长输入和中文编码。临时测试 Pod 结束后由 `--rm` 删除。

## 9. 暴露服务

仓库默认不创建 Ingress、LoadBalancer 或 NodePort，因为域名、证书、入口控制器、网络边界和认证方式属于目标环境决策。

如需外部访问，应由部署负责人新增经过评审的入口资源，并验证 TLS、认证、限流、请求体限制、日志脱敏和跨域策略。不要把本地端口转发当作生产入口证据。

## 10. 更新与回滚

每次发布使用新的不可变镜像摘要，修改 Deployment 后重新执行 dry-run、apply 和 rollout status。

```console
kubectl rollout history deployment/comment-classifier
kubectl get replicasets -l app=comment-classifier -o wide
```

只有确认历史版本仍满足数据、模型、接口和安全要求时，才执行经批准的回滚。回滚后必须重新验证 `/health`、`/predict`、日志和关键指标。

## 11. 验收证据

至少保存以下信息：

- Git 提交；
- `python:3.13.15-slim` 的实际基础镜像摘要；
- 发布镜像完整摘要；
- `training_metadata.json` 中的模型版本与基础模型 revision；
- dry-run、rollout、Pod、Service、事件和接口测试结果；
- 集群、命名空间、时间范围、执行人和审批记录；
- 未覆盖的 TLS、认证、容量、监控和回滚项。

在这些实时证据完成前，Kubernetes 验证状态为 `UNKNOWN`。
