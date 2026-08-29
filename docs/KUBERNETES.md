# Kubernetes 部署

本文只部署已经训练并验证的发布镜像。用户侧所有操作仍通过标准 Docker CLI 完成，不要求安装宿主机 `kubectl`。Kubernetes Pod 不负责训练，也不下载基础模型。

## 1. 当前发布镜像

仓库清单已固定到本次验证通过的不可变镜像摘要：

```text
docker.io/songleo/comment-classification-e2e@sha256:a971d00cc98932d08be4de1f65e14fc3af9dcdd3f768079ce14e472495c10b22
```

默认清单包含一个 Deployment 和一个 ClusterIP Service，并配置 `/health` 探针、CPU/内存 requests 与 limits、非 root、只读根文件系统和禁用权限提升。

## 2. 只用 Docker 校验清单

以下步骤不需要 Kubernetes 集群。先拉取固定版本的校验镜像：

```console
docker pull ghcr.io/yannh/kubeconform:v0.7.0
```

创建一个不启动的校验容器，把仓库中的清单复制进去，再启动校验：

```console
docker create --name comment-classifier-manifest-check ghcr.io/yannh/kubeconform:v0.7.0 -strict -summary /kubernetes.yaml
docker cp deploy/kubernetes.yaml comment-classifier-manifest-check:/kubernetes.yaml
docker start --attach comment-classifier-manifest-check
docker rm comment-classifier-manifest-check
```

预期摘要为 2 个资源均有效，Invalid、Errors 和 Skipped 都为 0。这个结果只证明清单符合内置 Kubernetes 资源 schema，不代表目标集群的准入策略或实际部署通过。

## 3. 集群部署前提

实际访问集群时仍只需要 Docker，但必须额外取得目标集群管理员批准的 kubeconfig。部署方还需要确认命名空间、镜像拉取策略、TLS、认证、网络策略、监控和回滚要求。

把获批 kubeconfig 以文件名 `kubeconfig` 放在项目根目录。该文件已被 Git 忽略，不得提交。然后用 Docker 命名卷保存本次部署输入：

```console
docker volume create comment-classifier-kubernetes-input
docker create --name comment-classifier-kubernetes-input-copy --mount type=volume,source=comment-classifier-kubernetes-input,target=/work --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 version --client
docker cp deploy/kubernetes.yaml comment-classifier-kubernetes-input-copy:/work/kubernetes.yaml
docker cp kubeconfig comment-classifier-kubernetes-input-copy:/work/kubeconfig
docker rm comment-classifier-kubernetes-input-copy
```

这里使用 DaoCloud 加速拉取固定版本的 Kubernetes 官方 kubectl 镜像。kubeconfig 只进入本地 Docker 命名卷，不进入发布镜像或 Git。

## 4. 服务端 dry-run

在实际创建资源前，让目标集群验证资源定义、API 和准入策略：

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 apply --dry-run=server -f /work/kubernetes.yaml
```

没有获批集群或该命令没有通过时，到此停止，Kubernetes 状态保持 `UNKNOWN`。

## 5. 发布与观察

只有变更窗口和审批齐全时执行：

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 apply -f /work/kubernetes.yaml
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 rollout status deployment/comment-classifier --timeout=5m
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 get pods -l app=comment-classifier -o wide
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 get service comment-classifier
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 get events --sort-by=.lastTimestamp
```

如果 rollout 失败，读取 Pod 描述和日志：

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 describe pods -l app=comment-classifier
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 logs deployment/comment-classifier --all-containers=true --tail=200
```

## 6. 集群内验收

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 run comment-classifier-smoke --image=curlimages/curl:8.10.1 --restart=Never --rm -i --command -- curl -fsS http://comment-classifier/health
```

预测验收应至少覆盖四个标签、空字符串校验、超长输入和中文编码。临时测试 Pod 结束后由 `--rm` 删除。

## 7. 服务暴露边界

仓库默认不创建 Ingress、LoadBalancer 或 NodePort，因为域名、证书、入口控制器、网络边界和认证方式属于目标环境决策。

如需外部访问，应由部署负责人新增经过评审的入口资源，并验证 TLS、认证、限流、请求体限制、日志脱敏和跨域策略。不要把本地端口转发当作生产入口证据。

## 8. 更新、回滚与清理

每次发布都应使用新的不可变镜像摘要，并重新执行 schema 校验、服务端 dry-run、apply 和 rollout status。查看历史状态：

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 rollout history deployment/comment-classifier
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 get replicasets -l app=comment-classifier -o wide
```

只有确认历史版本仍满足数据、模型、接口和安全要求时，才执行经批准的回滚。回滚后必须重新验证 `/health`、`/predict`、日志和关键指标。

完成全部集群操作且不再需要本地 kubeconfig 副本时，删除 Docker 命名卷：

```console
docker volume rm comment-classifier-kubernetes-input
```

## 9. 验收证据

至少保存 Git 提交、基础镜像摘要、发布镜像摘要、模型版本、基础模型 revision、schema 校验、服务端 dry-run、rollout、Pod、Service、事件和接口测试结果，以及集群、命名空间、时间范围、执行人与审批记录。

当前只完成 Docker 容器内 schema 校验，没有获批集群、服务端 dry-run、rollout 或集群接口证据，因此 Kubernetes 实际部署状态仍为 `UNKNOWN`。
