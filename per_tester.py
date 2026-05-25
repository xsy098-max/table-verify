import csv
from collections import defaultdict

filepath = r'c:\Users\Administrator\Downloads\JUMP测试排期+周报-JUMP6月台服需求.csv'
rows = list(csv.reader(open(filepath, encoding='utf-8-sig')))

data_items = []
cur_plan = False
for i in range(10, len(rows)):
    r = rows[i]
    cc = [c.strip() for c in r if c.strip()]
    if not cc: continue
    if cc and cc[0] in ['战斗分界线', '关卡分界线']: continue
    v = r[0].strip() if len(r) > 0 else ''
    m = r[1].strip() if len(r) > 1 else ''
    sf = r[2].strip() if len(r) > 2 else ''
    d = r[3].strip() if len(r) > 3 else ''
    s = r[4].strip() if len(r) > 4 else ''
    t = r[7].strip() if len(r) > 7 else ''
    est_raw = r[10].strip() if len(r) > 10 else ''
    pr = r[11].strip() if len(r) > 11 else ''
    if v == '规划中': cur_plan = True; continue
    if v == '' and cur_plan: continue
    cur_plan = False
    if not (v or s or pr): continue
    ps = pr.replace('%', '').strip()
    pv = float(ps) if ps and ps.replace('.', '').isdigit() else 0.0
    data_items.append({'r': i + 1, 'v': v, 'm': m, 'sf': sf, 'd': d, 's': s, 't': t,
                       'est_raw': est_raw, 'p': pv})


# ============ 预计耗时 → 小时数 ============
def parse_hours(raw):
    raw = raw.strip().lower()
    if not raw:
        return 2.0  # 默认 2h
    if raw == '?':
        return 2.0
    if raw == '顺手的事儿':
        return 0.5  # 零碎小需求，0.5h
    # "3d" / "0.5d" / "2h" / "1h"
    if raw.endswith('d'):
        try:
            return float(raw[:-1]) * 8
        except:
            return 2.0
    if raw.endswith('h'):
        try:
            return float(raw[:-1])
        except:
            return 2.0
    return 2.0


for it in data_items:
    it['hours'] = parse_hours(it['est_raw'])

# ============ 统计 ============
total_items = len(data_items)
total_hours = sum(it['hours'] for it in data_items)
weighted_progress = sum(it['p'] * it['hours'] for it in data_items)
avg_progress = weighted_progress / total_hours if total_hours > 0 else 0

# ============ 进度区间 ============
buckets = {}
for it in data_items:
    p = it['p']
    if p >= 100:
        key = '100%'
    elif p >= 90:
        key = '90%~99%'
    elif p >= 70:
        key = '70%~89%'
    elif p >= 50:
        key = '50%~69%'
    elif p > 0:
        key = '1%~49%'
    else:
        key = '0%'
    if key not in buckets:
        buckets[key] = {'count': 0, 'hours': 0.0, 'w_progress': 0.0}
    buckets[key]['count'] += 1
    buckets[key]['hours'] += it['hours']
    buckets[key]['w_progress'] += it['p'] * it['hours']

print('=' * 75)
print('   JUMP 6月台服OBT 测试进度分析报告 (按预计耗时加权)')
print('=' * 75)
print()
print(f'  需求总条目数：{total_items}')
print(f'  预计总耗时：{total_hours:.1f}h ({total_hours / 8:.1f} 人天)')
print(f'  整体加权完成百分比：{avg_progress:.1f}%')
print(f'  (对比：不加权简单平均为 {sum(it["p"] for it in data_items) / total_items:.1f}%)')
print()

print('-' * 55)
print(f'  {"进度区间":<14s} {"条目数":>5s} {"耗时(h)":>8s} {"耗时占比":>8s}')
print('-' * 55)
order = ['100%', '90%~99%', '70%~89%', '50%~69%', '1%~49%', '0%']
for key in order:
    if key in buckets:
        b = buckets[key]
        print(f'  {key:<14s} {b["count"]:>5d} {b["hours"]:>8.1f} {b["hours"] / total_hours * 100:>7.1f}%')
print('-' * 55)


# ============ 按测试负责人 (加权) ============
ts = defaultdict(lambda: {'count': 0, 'hours': 0.0, 'w_progress': 0.0, 'items': []})
for it in data_items:
    tn = it['t'] if it['t'] else '(未指定)'
    ts[tn]['count'] += 1
    ts[tn]['hours'] += it['hours']
    ts[tn]['w_progress'] += it['p'] * it['hours']
    ts[tn]['items'].append(it)

print()
print('=' * 95)
print('   按测试负责人汇总表 (按预计耗时加权)')
print('-' * 95)
hdr = (f'{"负责人":<10s} {"条目":>4s} {"耗时h":>6s} {"人天":>5s} '
       f'{"100%":>5s} {"90-99":>5s} {"70-89":>5s} {"50-69":>5s} {"1-49":>5s} {"0%":>5s} '
       f'{"加权进度":>8s} {"简单平均":>8s}')
print(hdr)
print('-' * 95)
for tn in sorted(ts.keys(), key=lambda x: ts[x]['hours'], reverse=True):
    s = ts[tn]
    items = s['items']
    avg_w = s['w_progress'] / s['hours'] if s['hours'] > 0 else 0
    avg_s = sum(it['p'] for it in items) / s['count'] if s['count'] > 0 else 0
    c100 = sum(1 for x in items if x['p'] >= 100)
    c90 = sum(1 for x in items if 90 <= x['p'] < 100)
    c70 = sum(1 for x in items if 70 <= x['p'] < 90)
    c50 = sum(1 for x in items if 50 <= x['p'] < 70)
    c1 = sum(1 for x in items if 0 < x['p'] < 50)
    c0 = sum(1 for x in items if x['p'] == 0)
    bar = '#' * int(avg_w / 5)
    print(f'{tn:<10s} {s["count"]:>4d} {s["hours"]:>6.1f} {s["hours"]/8:>5.1f} '
          f'{c100:>5d} {c90:>5d} {c70:>5d} {c50:>5d} {c1:>5d} {c0:>5d} '
          f'{avg_w:>7.1f}%  {avg_s:>7.1f}%  {bar}')
print('-' * 95)
print('  注："简单平均"是不加权的进度，供对比；"加权进度"是考虑了预计耗时的进度。')
print()

# ============ 各负责人详情 ============
for tn in sorted(ts.keys(), key=lambda x: ts[x]['hours'], reverse=True):
    s = ts[tn]
    avg_w = s['w_progress'] / s['hours'] if s['hours'] > 0 else 0
    print('=' * 65)
    print(f'  {tn}: {s["count"]}条 | {s["hours"]:.1f}h ({s["hours"]/8:.1f}人天) | 加权进度 {avg_w:.1f}%')
    print('-' * 65)
    for it in sorted(s['items'], key=lambda x: (x['p'], -x['hours']), reverse=True):
        p_str = '{:.0f}%'.format(it['p']) if it['p'] > 0 else '  --'
        lbl = it['m'] if it['m'] else '(子)'
        print('  {:>4s} [{:4s}] {:>5.1f}h | {:<8s} | {}'.format(
            p_str, it['s'], it['hours'], lbl, it['d'][:45]))
    print()
