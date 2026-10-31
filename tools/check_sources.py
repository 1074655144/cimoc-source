# -*- coding: utf-8 -*-
"""Cimoc 图源可达性探测：读取 sourceBaseUrl.json，并发探测所有 baseUrl/serverUrl。"""
import json, ssl, sys, time
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

SRC = sys.argv[1] if len(sys.argv) > 1 else 'gh.json'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'probe_result.json'

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Mobile Safari/537.36')
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def iter_urls(data):
    """产出 (图源ID, 字段, url)"""
    for key, val in data.items():
        if isinstance(val, str):
            if val.startswith('http'):
                yield key, '', val
        elif isinstance(val, dict):
            for fk, fv in val.items():
                if isinstance(fv, str) and fv.startswith('http'):
                    yield key, fk, fv


def probe(url, timeout=10):
    """返回 (status, final_url, err)"""
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    })
    opener = urllib.request.build_opener(
        urllib.request.HTTPRedirectHandler(), urllib.request.HTTPSHandler(context=CTX))
    t0 = time.time()
    try:
        with opener.open(req, timeout=timeout) as r:
            body = r.read(2048)
            return r.status, r.geturl(), None, round(time.time() - t0, 2), len(body)
    except urllib.error.HTTPError as e:
        # HTTPError 也是"服务器有响应"，403/404 可能只是反爬
        return e.code, url, 'HTTPError', round(time.time() - t0, 2), 0
    except Exception as e:
        return 0, url, type(e).__name__ + ':' + str(e)[:60], round(time.time() - t0, 2), 0


def main():
    data = json.load(open(SRC, encoding='utf-8'))
    items = list(iter_urls(data))
    print('待探测 URL 数：%d' % len(items), flush=True)

    def work(it):
        key, field, url = it
        st, final, err, el, sz = probe(url)
        host0 = urlparse(url).netloc
        host1 = urlparse(final).netloc if final else ''
        return {
            'key': key, 'field': field, 'url': url, 'status': st,
            'final': final, 'err': err, 'elapsed': el, 'size': sz,
            'host': host0, 'final_host': host1,
            'redirected': bool(host1 and host1 != host0),
        }

    with ThreadPoolExecutor(max_workers=24) as ex:
        res = list(ex.map(work, items))

    json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    ok = [r for r in res if 200 <= r['status'] < 400]
    bad = [r for r in res if r['status'] == 0]
    httpbad = [r for r in res if r['status'] >= 400]
    redir = [r for r in res if r['redirected']]
    print('\n可用(2xx/3xx): %d   连接失败: %d   HTTP错误(4xx/5xx): %d   域名跳转: %d'
          % (len(ok), len(bad), len(httpbad), len(redir)))

    print('\n===== 连接失败（需修复）=====')
    for r in sorted(bad, key=lambda x: x['key']):
        print('  %-22s %-10s %-40s %s' % (r['key'], r['field'], r['url'], r['err']))

    print('\n===== HTTP 错误 =====')
    for r in sorted(httpbad, key=lambda x: x['key']):
        print('  %-22s %-10s %-40s HTTP %s' % (r['key'], r['field'], r['url'], r['status']))

    print('\n===== 域名发生跳转（可更新为新域名）=====')
    for r in sorted(redir, key=lambda x: x['key']):
        print('  %-22s %-10s %-40s -> %s' % (r['key'], r['field'], r['url'], r['final']))


if __name__ == '__main__':
    main()
