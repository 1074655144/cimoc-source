# -*- coding: utf-8 -*-
"""生成修复后的 sourceBaseUrl.json：
1. 只修复"确认失效"的字段（DNS/TCP 不通、跳广告停放页、主站 404）
2. 域名活着但 403/超时的一律保留（多为反爬/防盗链/网络差异，换掉反而可能弄坏）
3. 候选来源：top/miu 版本差异、已验证的新域名、协议/子域变体
4. 每个替换值都实测通过才写入
"""
import json, ssl, re, socket, time, random
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
BAD_HOST = ('urldance', 'cerdma', 'parked', 'sedoparking', 'domainmarket', 'above.com', 'hugedomains')

# 手工确认的新域名映射：(图源ID, 字段) -> [候选，按优先级]
MANUAL = {
    ('GUFENG', ''): ['https://www.gufengmh9.com'],
    ('GuFengManHua', 'baseUrl'): ['https://www.gufengmh9.com'],
    ('GuFengWang', 'baseUrl'): ['https://gufengmanhua.cn'],
    ('YIMMH', 'baseUrl'): ['https://www.yimmh.com'],
    ('YiManHua', 'baseUrl'): ['https://www.yimmh.com'],
    ('IKANMAN', ''): ['https://www.manhuagui.cc'],
    ('CCTUKU', ''): ['https://www.tuku.cc'],
}

SRC = 'gh.json'


def flat(f):
    d = json.load(open(f, encoding='utf-8')); o = {}
    for k, v in d.items():
        if isinstance(v, str): o[(k, '')] = v
        elif isinstance(v, dict):
            for kk, vv in v.items():
                if isinstance(vv, str): o[(k, kk)] = vv
    return o


def is_url(s):
    return isinstance(s, str) and s.startswith('http')


def variants(u):
    p = urlparse(u); host = p.netloc.split(':')[0]; path = p.path or '/'
    base = host[4:] if host.startswith('www.') else host
    base = base[2:] if base.startswith('m.') else base
    out = []
    for s in (['https', 'http'] if p.scheme == 'https' else ['http', 'https']):
        for h in dict.fromkeys([host, base, 'www.' + base, 'm.' + base]):
            out.append('%s://%s%s' % (s, h, path if path != '/' else '/'))
    return out


def get(url, timeout=15):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Accept': 'text/html,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9'})
    op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))
    try:
        with op.open(req, timeout=timeout) as r:
            b = r.read(4096).decode('utf-8', 'ignore')
            m = re.search(r'<title[^>]*>(.*?)</title>', b, re.S | re.I)
            return r.status, r.geturl(), (m.group(1).strip()[:50] if m else '')
    except urllib.error.HTTPError as e:
        return e.code, url, 'HTTPError'
    except Exception as e:
        return 0, url, type(e).__name__


def tcp_ok(host, port, timeout=6):
    try:
        s = socket.create_connection((host, port), timeout=timeout); s.close(); return True
    except Exception:
        return False


def main():
    gh, top, miu = flat('gh.json'), flat('top.json'), flat('miu.json')
    conf = {c['url']: c for c in json.load(open('confirm_result.json', encoding='utf-8'))}
    data = json.load(open(SRC, encoding='utf-8'))

    # 1) 判定哪些字段需要修复
    need = []
    for k, v in gh.items():
        if not is_url(v):
            continue
        c = conf.get(v)
        if not c:
            continue
        fh = (c.get('final') or v)
        bad_host = any(b in urlparse(fh).netloc.lower() for b in BAD_HOST)
        if not c['tcp'] or bad_host:
            need.append((k, v, 'tcp_dead' if not c['tcp'] else 'parked'))
    print('确认失效需修复：%d 个字段' % len(need))

    # 2) 构建候选
    jobs = []
    for k, v, _reason in need:
        cands = list(MANUAL.get(k, []))
        for f in (top, miu):
            if is_url(f.get(k)):
                cands.append(f[k])
        cands.extend(variants(v))
        seen, uniq = set(), []
        for c in cands:
            if c not in seen and c != v:
                seen.add(c); uniq.append(c)
        for c in uniq[:8]:
            jobs.append((k, v, c))
    print('候选验证请求：%d' % len(jobs))

    def work(j):
        k, v, c = j
        time.sleep(random.uniform(0, 0.5))
        st, final, title = get(c)
        fh = urlparse(final).netloc.lower()
        ok = (200 <= st < 400) and not any(b in fh for b in BAD_HOST)
        return {'key': k, 'orig': v, 'cand': c, 'status': st, 'title': title, 'ok': ok}

    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(work, jobs))

    # 3) 择优
    chosen, unresolved = {}, []
    for k, v, _reason in need:
        rs = [r for r in res if r['key'] == k and r['ok']]
        if rs:
            best = rs[0]
            chosen[k] = best['cand']
            print('  ✓ %-20s %-14s %s\n      -> %s  [HTTP %s] %s'
                  % (k[0], k[1], v, best['cand'], best['status'], best['title'][:34]))
        else:
            unresolved.append((k, v))
            print('  ✗ %-20s %-14s %s   （无可用替代）' % (k[0], k[1], v))

    # 4) 写回
    for (kid, field), newval in chosen.items():
        node = data.get(kid)
        if isinstance(node, str):
            data[kid] = newval
        elif isinstance(node, dict) and field in node:
            node[field] = newval

    json.dump(data, open('sourceBaseUrl.fixed.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    json.dump({'fixed': [[list(k), v] for k, v in chosen.items()],
               'unresolved': [[list(k), v] for k, v in unresolved]},
              open('fix_report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n已修复 %d 个字段，仍无解 %d 个' % (len(chosen), len(unresolved)))
    print('输出：sourceBaseUrl.fixed.json')


if __name__ == '__main__':
    main()
