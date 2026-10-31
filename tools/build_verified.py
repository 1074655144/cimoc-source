# -*- coding: utf-8 -*-
"""生成精选可用版：只保留内容验证确认是漫画站的图源，并应用新域名替换。
同时输出一份「每个源能不能用」的完整清单供人工查看。"""
import json, shutil
from collections import OrderedDict

data = json.load(open('repo/sourceBaseUrl.json', encoding='utf-8'))
c2 = {r['id']: r for r in json.load(open('content_check2.json', encoding='utf-8'))}
recheck = {r['id']: r for r in json.load(open('recheck_result.json', encoding='utf-8'))}
newdom = json.load(open('new_domains.json', encoding='utf-8'))

# 只采用内容验证确实通过的新域名（避免替换成不相关的站）
SAFE_REPLACE = {
    'QIMANHUA': 'https://www.qiman6.com',
    'GoDaMH': 'https://www.godamanga.com',
    'IKANMANTW': 'https://www.manhuagui.cc',
}

def base_of(v):
    return v if isinstance(v, str) else (v.get('baseUrl') or '' if isinstance(v, dict) else '')

def set_base(v, url):
    if isinstance(v, str):
        return url
    if isinstance(v, dict):
        v = dict(v)
        if 'baseUrl' in v:
            v['baseUrl'] = url
            return v
    return v

verified = OrderedDict()
for kid, v in data.items():
    r = c2.get(kid)
    if not r or r['verdict'] != 'ok':
        continue
    nv = v
    if kid in SAFE_REPLACE:
        nv = set_base(v, SAFE_REPLACE[kid])
    verified[kid] = nv

json.dump(verified, open('repo/sourceBaseUrl.verified.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# 完整清单：每个源的状态
report = []
for kid, v in data.items():
    r = c2.get(kid, {})
    rc = recheck.get(kid, {})
    verdict = r.get('verdict', 'unknown')
    if verdict == 'ok':
        status, note = '可用', r.get('note', '')
    elif verdict == 'dead':
        status, note = '不可用', r.get('note', '')
    else:
        status = '可疑'
        note = r.get('note', '') + (' / 复核:' + rc.get('note', '') if rc else '')
    if kid in SAFE_REPLACE:
        note += '  [已换新域名]'
    report.append({'id': kid, 'status': status, 'url': base_of(v), 'note': note})
json.dump(report, open('repo/source_status.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

ok = [x for x in report if x['status'] == '可用']
bad = [x for x in report if x['status'] == '不可用']
susp = [x for x in report if x['status'] == '可疑']
print('精选可用版：%d 个图源' % len(verified))
print('\n全部 %d 个源的状态分布：可用 %d / 可疑 %d / 不可用 %d'
      % (len(report), len(ok), len(susp), len(bad)))
print('\n已应用新域名替换：')
for k, v in SAFE_REPLACE.items():
    if k in verified:
        print('  %-14s -> %s' % (k, v))
