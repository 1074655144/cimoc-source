# -*- coding: utf-8 -*-
"""对 dead + suspicious 图源做多轮复核：每个源在不同时间点请求 3 次，
任一次拿到漫画站内容即判定可用，消除限流/抖动造成的假阴性。"""
import json, ssl, re, time, random
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

UA_PC = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
         '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
UA_M = ('Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36')
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
COMIC_HINT = ['漫画', '动漫', '连载', '連載', '章节', '全集', 'comic', 'manga', 'manhua',
              'webtoon', '漫畫', '動漫', 'hentai']
JUNK_HINT = ['casino', 'bet365', '博彩', '赌博', '赌场', '彩票', 'urldance', 'sedoparking', 'viagra']
LINK_PAT = re.compile(r'href=["\'](?:https?://[^/]+)?/(?:comic|manhua|manga|book|mh|cartoon|chapter|comics?)[^"\']{0,60}["\']', re.I)


def base_of(v):
    return v if isinstance(v, str) else (v.get('baseUrl') or '' if isinstance(v, dict) else '')


def fetch(url, ua, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': ua,
                                               'Accept': 'text/html,*/*;q=0.8',
                                               'Accept-Language': 'zh-CN,zh;q=0.9'})
    op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))
    try:
        with op.open(req, timeout=timeout) as r:
            return r.status, r.geturl(), r.read(65536).decode('utf-8', 'ignore')
    except urllib.error.HTTPError as e:
        return e.code, url, ''
    except Exception:
        return 0, url, ''


def is_comic(txt, status):
    if not txt:
        return False, 'HTTP %s 无内容' % status
    low = txt.lower()
    if any(h in low for h in JUNK_HINT):
        return False, '变质页'
    comic = [h for h in COMIC_HINT if h in low]
    links = len(LINK_PAT.findall(txt))
    if comic or links >= 3:
        return True, '特征[%s]链接%d' % (','.join(comic[:2]) or '-', links)
    if status == 403:
        return True, '403但有响应(反爬)，域名存活'
    return False, '无漫画特征(%d字节)' % len(txt)


def probe(item):
    kid, url = item
    url = url.rstrip('/') + '/'
    results = []
    for i in range(3):
        ua = UA_PC if i % 2 == 0 else UA_M
        st, final, txt = fetch(url, ua)
        ok, note = is_comic(txt, st)
        results.append({'status': st, 'ok': ok, 'note': note})
        if ok:
            break
        time.sleep(1.2 + random.uniform(0, 0.8))
    good = [r for r in results if r['ok']]
    return {'id': kid, 'url': url, 'alive': bool(good),
            'note': good[0]['note'] if good else results[-1]['note'],
            'tries': [r['status'] for r in results]}


def main():
    c2 = json.load(open('content_check2.json', encoding='utf-8'))
    data = json.load(open('repo/sourceBaseUrl.json', encoding='utf-8'))
    targets = [(r['id'], base_of(data.get(r['id'])))
               for r in c2 if r['verdict'] in ('dead', 'suspicious')]
    targets = [t for t in targets if t[1].startswith('http')]
    print('待复核：%d' % len(targets), flush=True)

    with ThreadPoolExecutor(max_workers=5) as ex:
        res = list(ex.map(probe, targets))
    json.dump(res, open('recheck_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    alive = [r for r in res if r['alive']]
    still = [r for r in res if not r['alive']]
    print('\n复核后可用：%d' % len(alive))
    print('复核后仍不可用：%d' % len(still))
    print('\n===== 复核后恢复可用 =====')
    for r in sorted(alive, key=lambda x: x['id']):
        print('  %-20s %-40s %s  %s' % (r['id'], r['url'][:40], r['tries'], r['note'][:30]))
    print('\n===== 确认不可用 =====')
    for r in sorted(still, key=lambda x: x['id']):
        print('  %-20s %-40s %s  %s' % (r['id'], r['url'][:40], r['tries'], r['note'][:34]))


if __name__ == '__main__':
    main()
