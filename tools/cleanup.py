# -*- coding: utf-8 -*-
"""在修复版基础上移除"域名彻底废弃"的图源条目。
严格判据（避免误删）：
  - DNS 完全无法解析（域名已注销），或
  - 跳转到广告/停放页（域名被抢注）
仅超时 / 403 / 404 的一律保留（多为反爬、防盗链或本机网络差异）。
"""
import json, shutil
from urllib.parse import urlparse

BAD_HOST = ('urldance', 'cerdma', 'parked', 'sedoparking', 'domainmarket', 'above.com', 'hugedomains')

fixed = json.load(open('sourceBaseUrl.fixed.json', encoding='utf-8'))
rep = json.load(open('fix_report.json', encoding='utf-8'))
conf = {c['url']: c for c in json.load(open('confirm_result.json', encoding='utf-8'))}
unresolved = {tuple(k): v for k, v in rep['unresolved']}

DEAD = []
for (kid, field), v in unresolved.items():
    c = conf.get(v)
    if not c:
        continue
    fh = (c.get('final') or v)
    parked = any(b in urlparse(fh).netloc.lower() for b in BAD_HOST)
    if c['dns'] and not parked:
        continue                      # 域名还在，只是超时/被拦 -> 保留
    node = fixed.get(kid)
    cur = node if isinstance(node, str) else (node or {}).get(field)
    if isinstance(cur, str) and cur == v:
        DEAD.append((kid, field, v, 'parked' if parked else 'dns_dead'))

print('准备移除（域名彻底废弃）：%d' % len(DEAD))
for k, f, v, why in DEAD:
    print('  %-18s %-10s %-38s [%s]' % (k, f or '(主)', v, why))

slim = json.loads(json.dumps(fixed, ensure_ascii=False))
removed, dropped_field = [], []
for kid, field, v, why in DEAD:
    if kid not in slim:
        continue
    node = slim[kid]
    # 主站字段(baseUrl/裸串)失效 -> 整个图源不可用，移除条目
    if field in ('', 'baseUrl'):
        removed.append({'id': kid, 'url': v, 'reason': why, 'node': slim.pop(kid)})
    elif isinstance(node, dict) and field in node:
        # 辅助字段(图片/API 服务器)失效 -> 只删该字段，图源主体保留
        dropped_field.append({'id': kid, 'field': field, 'url': v, 'reason': why})
        del node[field]

json.dump(slim, open('sourceBaseUrl.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
shutil.copy('sourceBaseUrl.fixed.json', 'sourceBaseUrl.full.json')
json.dump({'removed_sources': removed, 'dropped_fields': dropped_field},
          open('removed_sources.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('\n精简版条目：%d   完整版条目：%d' % (len(slim), len(fixed)))
print('移除整条图源：%d   仅删除失效字段：%d' % (len(removed), len(dropped_field)))
