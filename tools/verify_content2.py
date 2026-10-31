# -*- coding: utf-8 -*-
"""逐源验证「能否打开漫画」v2（更稳健）：
- 先验证首页 baseUrl 判断站点身份，再验证搜索页能否返回漫画列表
- 失败项自动重试（换 UA / 换协议 / 加长超时）
- 特征词收紧，避免误伤正规站（去掉 seo/slot 这类过宽的词）
"""
import json, ssl, re, time, random, sys
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, quote

UA_PC = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
         '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
UA_M = ('Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36')
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE

# 漫画站内容特征（收紧）
COMIC_HINT = ['漫画', '动漫', '连载', '連載', '章节', '章節', '全集', '在线阅读', '在线看',
              '国漫', '國漫', '日漫', '韩漫', '绘本', 'comic', 'manga', 'manhua',
              'webtoon', 'hentai', 'doujin', '動漫', '漫畫']
# 明确的垃圾/变质站特征（收紧，避免误伤）
JUNK_HINT = ['casino', 'bet365', '博彩', '赌博', '赌场', '彩票', 'poker',
             'urldance', 'sedoparking', 'buy this domain', 'domain parking',
             '此域名正在出售', '网站出售', 'viagra', 'pornhub', 'xxxvideo']
# 漫画站常见的链接路径模式
LINK_PAT = re.compile(
    r'href=["\'](?:https?://[^/]+)?/(?:comic|manhua|manga|book|mh|cartoon|'
    r'chapter|series|title|works|comics?|dm|ac)[^"\']{0,60}["\']', re.I)

KEYWORD = '斗罗大陆'


def base_of(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return v.get('baseUrl') or ''
    return ''


def search_url(v):
    b = base_of(v).rstrip('/')
    if isinstance(v, dict):
        s = v.get('search') or v.get('searchUrl') or ''
        if '%s' in s:
            try:
                return b + (s % quote(KEYWORD))
            except Exception:
                return b + s.replace('%s', quote(KEYWORD))
    return None


def fetch(url, ua=UA_PC, timeout=18):
    req = urllib.request.Request(url, headers={
        'User-Agent': ua, 'Accept': 'text/html,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9'})
    op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))
    try:
        with op.open(req, timeout=timeout) as r:
            raw = r.read(65536)
            txt = raw.decode('utf-8', 'ignore')
            return r.status, r.geturl(), txt
    except urllib.error.HTTPError as e:
        return e.code, url, ''
    except Exception:
        return 0, url, ''


def try_all(url):
    """重试：桌面UA -> 移动端UA -> 协议互换"""
    attempts = [(url, UA_PC)]
    if url.startswith('https://'):
        attempts.append((url.replace('https://', 'http://', 1), UA_M))
    else:
        attempts.append((url.replace('http://', 'https://', 1), UA_M))
    attempts.append((url, UA_M))
    best = (0, url, '')
    for u, ua in attempts:
        st, final, txt = fetch(u, ua)
        if 200 <= st < 400 and txt:
            return st, final, txt
        if best[0] == 0 or (st and st < best[0] if best[0] else False):
            best = (st, final, txt)
        if st == 403:
            best = (st, final, txt)
        time.sleep(0.3)
    return best


def classify(txt, status):
    if not txt:
        return 'dead', 'HTTP %s / 无响应' % status
    low = txt.lower()
    junk = [h for h in JUNK_HINT if h in low]
    if junk:
        return 'dead', '变质为: ' + ','.join(junk[:2])
    comic = [h for h in COMIC_HINT if h in low]
    links = len(LINK_PAT.findall(txt))
    if comic or links >= 3:
        return 'ok', '漫画特征[%s] 链接%d' % (','.join(comic[:2]) or '-', links)
    if len(txt) < 800:
        return 'suspicious', '响应过短(%d)，可能JS跳转或反爬' % len(txt)
    return 'suspicious', '有内容但无漫画特征(%d字节)' % len(txt)


def work(item):
    kid, v = item
    b = base_of(v)
    if not b.startswith('http'):
        return {'id': kid, 'verdict': 'skip', 'note': '无baseUrl', 'url': ''}
    time.sleep(random.uniform(0, 0.5))
    st, final, txt = try_all(b.rstrip('/') + '/')
    vd, note = classify(txt, st)
    rec = {'id': kid, 'verdict': vd, 'note': note, 'home': b, 'status': st,
           'final': final, 'size': len(txt)}
    # 首页通过后再验搜索
    if vd == 'ok':
        su = search_url(v)
        if su:
            sst, sfin, stxt = try_all(su)
            low = stxt.lower()
            hit = any(h in low for h in COMIC_HINT) or len(LINK_PAT.findall(stxt)) >= 3
            rec['search_status'] = sst
            rec['search_ok'] = bool(hit and sst and sst < 400)
            rec['search_url'] = su
    return rec


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else 'repo/sourceBaseUrl.json'
    data = json.load(open(src, encoding='utf-8'))
    items = [(k, v) for k, v in data.items() if base_of(v).startswith('http')]
    print('待验证图源：%d' % len(items), flush=True)
    with ThreadPoolExecutor(max_workers=5) as ex:
        res = list(ex.map(work, items))
    json.dump(res, open('content_check2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    ok = [r for r in res if r['verdict'] == 'ok']
    srch_ok = [r for r in ok if r.get('search_ok')]
    susp = [r for r in res if r['verdict'] == 'suspicious']
    dead = [r for r in res if r['verdict'] == 'dead']
    print('\n首页确认为漫画站 : %d' % len(ok))
    print('  其中搜索也能返回漫画 : %d' % len(srch_ok))
    print('可疑(需人工确认) : %d' % len(susp))
    print('无效(打不开/变质): %d' % len(dead))

    print('\n===== 完全可用（首页+搜索均正常）=====')
    for r in sorted(srch_ok, key=lambda x: x['id']):
        print('  %-22s %-42s' % (r['id'], r['home'][:42]))
    print('\n===== 首页可用但搜索未验证/无搜索规则 =====')
    for r in sorted([x for x in ok if not x.get('search_ok')], key=lambda x: x['id']):
        print('  %-22s %-42s %s' % (r['id'], r['home'][:42], r['note'][:34]))
    print('\n===== 无效 =====')
    for r in sorted(dead, key=lambda x: x['id']):
        print('  %-22s %-42s %s' % (r['id'], r['home'][:42], r['note'][:34]))
    print('\n===== 可疑 =====')
    for r in sorted(susp, key=lambda x: x['id']):
        print('  %-22s %-42s %s' % (r['id'], r['home'][:42], r['note'][:34]))


if __name__ == '__main__':
    main()
