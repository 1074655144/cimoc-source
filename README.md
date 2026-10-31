# Cimoc 漫画图源订阅（修复版）

Cimoc 漫画 App 的图源订阅文件 `sourceBaseUrl.json`。

上游 `https://gitee.com/Haleydu/update/raw/master/sourceBaseUrl-json` 已被 Gitee 封禁
（返回 423 `The Repository has been blocked`），无法再作为图源地址导入。
本仓库在其最后一份可用快照基础上，批量探测并修复了失效的漫画源。

## 导入地址

### 推荐：精选可用版（47 个源，逐个验证过能打开漫画）

```
https://cdn.jsdelivr.net/gh/1074655144/cimoc-source@main/sourceBaseUrl.verified.json
```

### 覆盖更广的修复版（141 个源，含部分未逐个验证的）

```
https://cdn.jsdelivr.net/gh/1074655144/cimoc-source@main/sourceBaseUrl.json
```

上面两个走的是 jsDelivr 镜像，国内通常可直接访问。若 jsDelivr 也不通，
把前缀换成 raw 试试：

```
https://raw.githubusercontent.com/1074655144/cimoc-source/main/sourceBaseUrl.verified.json
```

仓库地址：https://github.com/1074655144/cimoc-source

## 该导入哪个

| 如果你想 | 导入这个 | 图源数 |
| --- | --- | --- |
| **要"每个源都能用"** | `sourceBaseUrl.verified.json` | **47** |
| 要覆盖广、能容忍部分源失效 | `sourceBaseUrl.json` | 141 |
| 要和官方原版结构完全一致 | `sourceBaseUrl.full.json` | 155 |

`verified` 版是逐个抓取页面内容验证过的：只保留确实返回漫画内容的站点，
剔除了打不开的、变质成赌博/广告页的、以及返回空壳跳转页的域名。

想看每个源具体情况，打开 `source_status.html`（141 个源逐条列出状态、
地址和判定依据，可按状态筛选、按名称搜索）。

## 文件说明

| 文件 | 说明 |
| --- | --- |
| `sourceBaseUrl.verified.json` | **精选可用版**。逐个源抓取页面验证过，47 个 |
| `sourceBaseUrl.json` | 修复版。修复域名 + 移除已彻底废弃的图源，141 个 |
| `sourceBaseUrl.full.json` | 完整版。仅替换失效域名，未删除任何图源，155 个 |
| `source_status.html` | **每个源能不能用**的可视化清单（可筛选/搜索，浏览器直接打开） |
| `source_status.json` | 同上，JSON 格式的原始数据 |
| `fix_report.json` | 修复明细：每个字段的旧值/新值，以及未能修复的清单 |
| `removed_sources.json` | 被移除的图源及其原 URL（含完整节点，便于日后恢复） |

## 已验证的可用图源（47 个）

BILIMANHUA、DUMANWU、DUMANWUORG、TTKANMANHUA、YYMANHUA、MANHUAYU、RUMANHUA、
HAODUOMAN、DASHUMANHUA、YOUMANHUAWU、DM5、DongManWu、MANHUATAI、ManHuaTai、
MANHUATAIPIC、U17、WEBTOON、WEBTOONDONGMANMANHUA、MIGU、TENCENT、TENCENTM、
IKANMAN、BAOZIV2、HaoManSix、CCTUKU、CoCoManHua、GODAMH、HaoManEight、
BODONGMH、HAOMAN6、HAOMAN8、BMG、BOLEMH、DMZJFIX、GuFengWang、LAIMH、
MANHUADB、MANHUAWU、MANMANMANHUA、MH160、MH160CC、PUFEI、PUFEIMH、PuFeiManHua、
VOMIC2、YKMH、YouKuManHua

## 已知失效的图源

**域名彻底连不上**：DMZJ 系列（动漫之家）、BAOZIMH / BaoziManHua（包子）、
COPYMH / CopyManHua（拷贝）、CHUIXUE（吹雪）、YIMMH / YiManHua（一米）、
MANGABZ、MANHUA90、MITUI、XMANHUA、YEMANMH、KOMIIC、BIQUGE、MYCOMIC、ANIMX2

**域名已变质**：SHOUJIMH / ShouJiManHua（gmanhua.com 变成赌博站）、
GoDaMH（godamanga.art 跳到 urldance 停放页）

**返回同一套空壳跳转页**（已不再是漫画站）：
DUMH / DuManHua、MH50 / ManHuaCat、QIMIAO / QIMIAOMH、SUMANKU、ZERO、YOUDM

> 注：探测从我所在网络发起，部分站点存在反爬/限流，实际结果可能随网络与
> 时间段波动。`source_status.json` 里有每个源的具体判定依据。

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
