# Kubernetes 部署

本文只部署已经训练并验证的发布镜像。用户侧所有通用操作仍通过标准 Docker CLI 完成，不要求安装宿主机 `kubectl`。Kubernetes Pod 不负责训练，也不下载基础模型。

2026-08-31 已在一个获批的单节点 demo 集群完成服务端 dry-run、rollout 和接口测试。这个结果只证明下文记录的 demo 范围，不代表生产环境验收。

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

以下命令使用独立命名空间 `comment-classifier-demo`，避免与集群中的其他应用混放。首次部署时创建该命名空间；如果已经存在，确认其归属无误后跳过创建命令：

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 create namespace comment-classifier-demo
```

## 4. 服务端 dry-run

在实际创建资源前，让目标集群验证资源定义、API 和准入策略：

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 apply --dry-run=server --namespace=comment-classifier-demo -f /work/kubernetes.yaml
```

没有获批集群或该命令没有通过时，到此停止，Kubernetes 状态保持 `UNKNOWN`。

## 5. 发布与观察

只有变更窗口和审批齐全时执行：

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 apply --namespace=comment-classifier-demo -f /work/kubernetes.yaml
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 rollout status --namespace=comment-classifier-demo deployment/comment-classifier --timeout=5m
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 get pods --namespace=comment-classifier-demo -l app=comment-classifier -o wide
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 get service --namespace=comment-classifier-demo comment-classifier
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 get events --namespace=comment-classifier-demo --sort-by=.lastTimestamp
```

如果 rollout 失败，读取 Pod 描述和日志：

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 describe pods --namespace=comment-classifier-demo -l app=comment-classifier
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 logs --namespace=comment-classifier-demo deployment/comment-classifier --all-containers=true --tail=200
```

## 6. 集群内验收

先直接在已经运行的发布容器中使用 Python 标准库访问 ClusterIP Service，避免额外测试镜像受目标集群镜像代理影响：

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 exec --namespace=comment-classifier-demo deployment/comment-classifier -- python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://comment-classifier/health')))"
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 exec --namespace=comment-classifier-demo deployment/comment-classifier -- python -c "import json,urllib.request; request=urllib.request.Request('http://comment-classifier/predict',data=json.dumps({'text':'\u9000\u6b3e\u7533\u8bf7\u8d85\u8fc7\u671f\u9650\u4ecd\u672a\u5904\u7406\uff0c\u8bf7\u4ecb\u5165'}).encode(),headers={'Content-Type':'application/json'}); print(json.load(urllib.request.urlopen(request)))"
```

预测验收应至少覆盖四个标签、空字符串校验、超长输入和中文编码。临时测试 Pod 结束后由 `--rm` 删除。

## 7. 服务暴露边界

仓库默认不创建 Ingress、LoadBalancer 或 NodePort，因为域名、证书、入口控制器、网络边界和认证方式属于目标环境决策。

如需外部访问，应由部署负责人新增经过评审的入口资源，并验证 TLS、认证、限流、请求体限制、日志脱敏和跨域策略。不要把本地端口转发当作生产入口证据。

本次 demo 为便于人工 review，额外创建了不在仓库默认清单中的 `comment-classifier-review` NodePort Service，端口为 `30081`。节点防火墙只增加了运行时规则，没有写入永久配置。这个入口没有 TLS 和认证，只能用于隔离的内部 demo 网络；通用部署不得照搬。

## 8. 2026-08-31 demo 实测记录

| 项目 | 实测结果 |
| --- | --- |
| 集群 | 单节点 k3s `v1.33.1+k3s1`，Rocky Linux 9.6，`linux/amd64` |
| 节点 | `Ready`，8 CPU，约 15.4 GiB 可分配内存 |
| 命名空间 | `comment-classifier-demo` |
| 服务端 dry-run | PASS，Deployment 与 ClusterIP Service 均通过 |
| 镜像 | 清单请求值与运行时 image ID 均为 `sha256:a971d00cc98932d08be4de1f65e14fc3af9dcdd3f768079ce14e472495c10b22` |
| rollout | PASS，Deployment `1/1 Available` |
| Pod | `1/1 Running`，重启次数 0 |
| 健康检查 | PASS，模型版本 `20260828T234758Z` |
| 四分类预测 | PASS，`positive`、`negative`、`neutral`、`complaint` 各一个独立测试集样例均命中预期标签 |
| 输入边界 | PASS，空字符串和 1001 字符输入均返回 HTTP 422 |
| 中文编码 | PASS，工作站经 NodePort 提交中文 JSON 并得到正确结果 |
| Swagger | PASS，demo NodePort 的 `/docs` 返回 HTTP 200 |

首次 rollout 遇到 `ImagePullBackOff`：该节点把 Docker Hub 重定向到 DaoCloud 公共镜像代理，而代理以“镜像不在白名单”拒绝请求。验证时没有修改或重启 k3s 的全局仓库配置，而是校验本地已验证镜像的摘要和离线包 SHA-256 后，将同一镜像导入 k3s 的 `k8s.io` containerd namespace，再重建失败 Pod。这个离线导入是当前 demo 环境的受控绕行，不代表 Docker Hub 在线拉取通过。

集群还有一个与本应用无关的既有问题：`metrics-server` readiness 返回 HTTP 500，因此 `kubectl top` 不可用。本次没有修改该组件，容量和监控验收仍不在 PASS 范围内。

当前 Deployment、两个 Service、运行时 NodePort 防火墙规则和 k3s 镜像缓存均按 review 要求保留，尚未执行清理。

## 9. 更新、回滚与清理

每次发布都应使用新的不可变镜像摘要，并重新执行 schema 校验、服务端 dry-run、apply 和 rollout status。查看历史状态：

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 rollout history --namespace=comment-classifier-demo deployment/comment-classifier
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 get replicasets --namespace=comment-classifier-demo -l app=comment-classifier -o wide
```

只有确认历史版本仍满足数据、模型、接口和安全要求时，才执行经批准的回滚。回滚后必须重新验证 `/health`、`/predict`、日志和关键指标。

经 review 明确批准后，先删除 demo-only NodePort Service，再删除仓库清单创建的资源和命名空间：

```console
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 delete service --namespace=comment-classifier-demo comment-classifier-review
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 delete --namespace=comment-classifier-demo -f /work/kubernetes.yaml
docker run --rm --mount type=volume,source=comment-classifier-kubernetes-input,target=/work,readonly --env KUBECONFIG=/work/kubeconfig --entrypoint kubectl m.daocloud.io/registry.k8s.io/kubectl:v1.34.1 delete namespace comment-classifier-demo
```

demo 节点管理员还需要删除 NodePort 的运行时防火墙规则；是否删除导入的镜像缓存应单独确认，不能由删除 Namespace 代替。完成全部集群操作且不再需要本地 kubeconfig 副本时，再删除 Docker 命名卷：

```console
docker volume rm comment-classifier-kubernetes-input
```

## 10. 验收证据

至少保存 Git 提交、基础镜像摘要、发布镜像摘要、模型版本、基础模型 revision、schema 校验、服务端 dry-run、rollout、Pod、Service、事件和接口测试结果，以及集群、命名空间、时间范围、执行人与审批记录。

当前单节点 demo 集群的服务端 dry-run、rollout、ClusterIP/NodePort 接口和输入边界测试均已通过。生产集群、TLS、认证、网络策略、监控、容量、漏洞扫描、签名、升级和回滚仍为 `UNKNOWN`。
