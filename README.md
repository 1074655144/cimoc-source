# Cimoc 漫画图源订阅（修复版）

Cimoc 漫画 App 的图源订阅文件 `sourceBaseUrl.json`。

上游 `https://gitee.com/Haleydu/update/raw/master/sourceBaseUrl-json` 已被 Gitee 封禁
（返回 423 `The Repository has been blocked`），无法再作为图源地址导入。
本仓库在其最后一份可用快照基础上，批量探测并修复了失效的漫画源。

## 导入地址

在 Cimoc 的「导入图源」中填入以下任一地址：

```
https://raw.githubusercontent.com/1074655144/cimoc-source/main/sourceBaseUrl.json
```

如果 GitHub raw 访问不畅，改用 jsDelivr 镜像：

```
https://cdn.jsdelivr.net/gh/1074655144/cimoc-source@main/sourceBaseUrl.json
```

仓库地址：https://github.com/1074655144/cimoc-source

## 文件说明

| 文件 | 说明 |
| --- | --- |
| `sourceBaseUrl.json` | **推荐导入**。修复域名 + 移除已彻底废弃的图源，141 个图源 |
| `sourceBaseUrl.full.json` | 完整版。仅替换失效域名，未删除任何图源，155 个 |
| `fix_report.json` | 修复明细：每个字段的旧值/新值，以及未能修复的清单 |
| `removed_sources.json` | 被移除的图源及其原 URL（含完整节点，便于日后恢复） |

## 修复方法

1. 从作者仍在维护的镜像取得基线（GitHub `haleydu-test/cimocUpdate`、
   `www.cimoc.top`、`miuscapp.com`），三方交叉比对取可用值。
2. 对全部 179 个 URL 做 **DNS 解析 → TCP 连通 → HTTP 请求** 三级探测。
3. 判据：只把 **DNS 无法解析** 或 **跳转到广告/停放页** 视为域名废弃；
   超时、403、404 一律保留（多为反爬、防盗链或网络差异，换掉反而可能弄坏）。
4. 每个替换值都实测返回 2xx 后才写入。

### 已修复的域名

| 图源 | 旧域名 | 新域名 |
| --- | --- | --- |
| GUFENG / GuFengManHua | m.gufengmh9.com、m.gufengmh.com | www.gufengmh9.com |
| GuFengWang | m.gufengmanhua.com | gufengmanhua.cn |
| YIMMH / YiManHua | m.yimmh.com | www.yimmh.com |
| IKANMAN（漫画柜） | www.manhuagui.com | www.manhuagui.cc |
| CCTUKU | m.tuku.cc | www.tuku.cc |
| MH517 | m.517mh.net | 517mh.net |
| MIGU | www.migudm.cn | m.migudm.cn |
| MANGABZ / MangaBZManHua | www.mangabz.com | mangabz.com |
| RUMANHUA | rumanhua1.com | rumanhua2.com |

### 已移除的图源（域名彻底废弃，无可用替代）

MH360、BUKA（布卡）、CCMH、CHUIYAO、SIXMH、TUHAO（土豪）、U17_SO、
DMZJPICTURE、DMZJFIXPICTURE、DMZJV2PICTURE、GUFENGSERVER、
MH160SERVER1/2/3

另有 16 个图片/API 服务器字段因域名失效被删除，对应图源主体保留（可搜索，但图片可能加载失败）。

## 说明

漫画站的域名更换频繁，本文件的修复结果只在探测当时有效。
建议定期重跑探测脚本更新；探测脚本位于本仓库 `tools/` 目录。
