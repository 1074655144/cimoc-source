# -*- coding: utf-8 -*-
"""域名猎捕：对已死域名生成变体（前缀/数字/后缀），批量 DNS 解析，通过的再做 HTTP 验证。"""
import json, socket, ssl, re, time
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
TLDS = ['com', 'cn', 'net', 'org', 'cc', 'top', 'xyz', 'site', 'online', 'fun',
        'vip', 'ink', 'link', 'club', 'tv', 'me', 'io', 'co', 'ltd', 'one', 'art', 'app']

# 已死域名 -> (基础名, 是否尝试数字变体)
BASES = {
    'gufengmh': dict(num=range(1, 10), sub=['m', 'www', '']),
    'gufengmanhua': dict(num=[], sub=['m', 'www', '']),
    '517mh': dict(num=[], sub=['m', 'www', '']),
    'ccmh16': dict(num=range(10, 30), sub=['m', 'www', '']),
    'chuiyao': dict(num=[], sub=['m', 'www', '']),
    'jsj66': dict(num=[], sub=['m', 'www', '']),
    'dmzj': dict(num=[], sub=['images', 'img', 'imagesold', 'www', 'm', 'v3api', 'api']),
    'kingwar': dict(num=[], sub=['mhpic5', 'mhpic6', 'mhpic1', 'mhpic2', 'mhpic3', 'mhpic4']),
    '100fanwo': dict(num=[], sub=['m', 'www', '']),
    'yimmh': dict(num=[], sub=['m', 'www', '']),
    'tueqi': dict(num=[], sub=['res.img', 'img', 'www']),
    'shut123': dict(num=range(1, 21), sub=['res10', 'res1', 'res', 'www']),
    'xiaoqinre': dict(num=[], sub=['res', 'www', 'img']),
    'g-mh': dict(num=[], sub=['f40-1-4', 't40-1-4', 'm', 'www', 'api-get-v2']),
    'gdbyhtl': dict(num=[], sub=['css', 'www', 'img']),
    'u17': dict(num=[], sub=['so', 'www', 'm']),
    'manhuagui': dict(num=[], sub=['www', 'tw', 'm']),
    'imitui': dict(num=[], sub=['www', 'm', '']),
    'xmanhua': dict(num=[], sub=['www', 'm', '']),
    'mangabz': dict(num=[], sub=['www', 'm', '']),
    'migudm': dict(num=[], sub=['www', 'm', '']),
    'hamreus': dict(num=[], sub=['i', 'www']),
}


def gen():
    out = set()
    for base, cfg in BASES.items():
        nums = list(cfg['num']) or ['']
        for n in nums:
            name = '%s%s' % (base, n)
            for tld in TLDS:
                for sub in cfg['sub']:
                    host = ('%s.%s.%s' % (sub, name, tld)) if sub else ('%s.%s' % (name, tld))
                    out.add(host)
    return sorted(out)


def dns(host):
    try:
        socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        return True
    except Exception:
        return False


def http(host, timeout=12):
    for scheme in ('https', 'http'):
        url = '%s://%s/' % (scheme, host)
        req = urllib.request.Request(url, headers={
            'User-Agent': UA, 'Accept': 'text/html,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9'})
        op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))
        try:
            with op.open(req, timeout=timeout) as r:
                b = r.read(4096).decode('utf-8', 'ignore')
                m = re.search(r'<title[^>]*>(.*?)</title>', b, re.S | re.I)
                return r.status, url, (m.group(1).strip()[:50] if m else '')
        except urllib.error.HTTPError as e:
            return e.code, url, 'HTTPError'
        except Exception as e:
            continue
    return 0, '', ''


def main():
    cands = gen()
    print('候选域名数：%d' % len(cands), flush=True)
    with ThreadPoolExecutor(max_workers=60) as ex:
        ok = [h for h, d in zip(cands, ex.map(dns, cands)) if d]
    print('DNS 可解析：%d' % len(ok), flush=True)
    json.dump(ok, open('dns_ok.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(lambda h: (h,) + http(h), ok))
    good = [r for r in res if r[1] and (200 <= r[1] < 400 or r[1] in (403,))]
    json.dump([{'host': r[0], 'status': r[1], 'url': r[2], 'title': r[3]} for r in res],
              open('hunt_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print('\n===== 探测到的可用域名 =====')
    for r in sorted(good, key=lambda x: x[0]):
        print('  %-34s HTTP %-4s %s  [%s]' % (r[0], r[1], r[2], r[3][:34]))


if __name__ == '__main__':
    main()
