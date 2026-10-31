# -*- coding: utf-8 -*-
"""稳健确认：低并发，按域名去重，依次做 DNS 解析(重试) -> TCP 连接 -> HTTPS/HTTP 握手 -> 轻量 GET。
判据：DNS 失败或 TCP 不可连 = 域名真死，需要替换；有 HTTP 响应(含403/404) = 域名活着，保留。"""
import json, socket, ssl, time, re, random
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE


def dns(host, tries=3):
    for i in range(tries):
        try:
            socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def tcp(host, port, timeout=8):
    for fam, addr in ((socket.AF_INET, (host, port)),):
        try:
            s = socket.create_connection(addr, timeout=timeout)
            s.close()
            return True
        except Exception:
            pass
    return False


def http(url, timeout=15):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))
    try:
        with op.open(req, timeout=timeout) as r:
            raw = r.read(4096)
            if r.headers.get('Content-Encoding') == 'gzip':
                import gzip; raw = gzip.decompress(raw)
            t = raw.decode('utf-8', 'ignore')
            m = re.search(r'<title[^>]*>(.*?)</title>', t, re.S | re.I)
            return r.status, r.geturl(), (m.group(1).strip()[:50] if m else '')
    except urllib.error.HTTPError as e:
        return e.code, url, 'HTTPError'
    except Exception as e:
        return 0, url, type(e).__name__ + ':' + str(e)[:40]


def main():
    data = json.load(open('gh.json', encoding='utf-8'))
    # 收集所有 url（以 gh 版本为准），并记录其他版本的候选
    def flat(f):
        d = json.load(open(f, encoding='utf-8')); o = {}
        for k, v in d.items():
            if isinstance(v, str): o[(k, '')] = v
            elif isinstance(v, dict):
                for kk, vv in v.items():
                    if isinstance(vv, str): o[(k, kk)] = vv
        return o
    g, t, m = flat('gh.json'), flat('top.json'), flat('miu.json')

    urls = sorted({v for v in g.values() if v.startswith('http')})
    print('去重后 URL 数：%d' % len(urls))

    def work(u):
        time.sleep(random.uniform(0, 0.8))
        p = urlparse(u)
        host, port = p.netloc, p.port or (443 if p.scheme == 'https' else 80)
        h = host.split(':')[0]
        d = dns(h)
        c = tcp(h, port) if d else False
        st, final, title = http(u) if c else (0, u, 'no-conn')
        return {'url': u, 'host': h, 'dns': d, 'tcp': c,
                'status': st, 'final': final, 'title': title}

    with ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(work, urls))
    json.dump(res, open('confirm_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    alive, dead = [], []
    for r in res:
        (alive if r['tcp'] else dead).append(r)
    print('\n域名活着(TCP可连)：%d   域名已死：%d' % (len(alive), len(dead)))
    print('\n===== 域名已死（必须换）=====')
    for r in dead:
        print('  %-46s dns=%s tcp=%s' % (r['url'], r['dns'], r['tcp']))
    print('\n===== 活着但 HTTP 非 2xx（多为反爬/防盗链，保留）=====')
    for r in alive:
        if not (200 <= r['status'] < 400):
            print('  %-46s HTTP %s  %s' % (r['url'], r['status'], r['title'][:30]))


if __name__ == '__main__':
    main()
