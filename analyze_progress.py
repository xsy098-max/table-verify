import csv

filepath = r'c:\Users\Administrator\Downloads\JUMP测试排期+周报-JUMP6月台服需求.csv'

rows = []
with open(filepath, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    for row in reader:
        rows.append(row)

# 解析所有数据行（从 row 11/索引10 开始）
data_items = []
current_planning = False

for i in range(10, len(rows)):
    r = rows[i]
    content_cells = [c.strip() for c in r if c.strip()]
    if not content_cells:
        continue
    # 跳过分界线
    if content_cells and content_cells[0] in ['战斗分界线', '关卡分界线']:
        continue

    version = r[0].strip() if len(r) > 0 else ''
    module = r[1].strip() if len(r) > 1 else ''
    sub_feature = r[2].strip() if len(r) > 2 else ''
    detail = r[3].strip() if len(r) > 3 else ''
    status = r[4].strip() if len(r) > 4 else ''
    tester = r[7].strip() if len(r) > 7 else ''
    progress_raw = r[11].strip() if len(r) > 11 else ''

    if version == '规划中':
        current_planning = True
        continue
    if version == '' and current_planning:
        continue
    if version == '':
        current_planning = False

    if not (version or status or progress_raw):
        continue

    current_planning = False

    # 解析进度百分比
    progress_str = progress_raw.replace('%', '').strip()
    if progress_str and progress_str.replace('.', '').isdigit():
        progress_val = float(progress_str)
    else:
        progress_val = 0.0

    data_items.append({
        'row': i + 1,
        'version': version,
        'module': module,
        'sub_feature': sub_feature,
        'detail': detail[:60] if detail else '',
        'status': status,
        'tester': tester,
        'progress_raw': progress_raw,
        'progress': progress_val,
    })

# ============ 核心统计 ============
total = len(data_items)

# 按进度区间分组
buckets = {
    '100%（已完成）': [],
    '90%～99%': [],
    '70%～89%': [],
    '50%～69%': [],
    '1%～49%': [],
    '0%（未开始/无进度）': [],
}

for item in data_items:
    p = item['progress']
    if p >= 100:
        buckets['100%（已完成）'].append(item)
    elif p >= 90:
        buckets['90%～99%'].append(item)
    elif p >= 70:
        buckets['70%～89%'].append(item)
    elif p >= 50:
        buckets['50%～69%'].append(item)
    elif p > 0:
        buckets['1%～49%'].append(item)
    else:
        buckets['0%（未开始/无进度）'].append(item)

# 整体加权进度
total_progress = sum(item['progress'] for item in data_items)
avg_progress = total_progress / total if total > 0 else 0

# 按模块统计
from collections import defaultdict
module_stats = defaultdict(lambda: {'count': 0, 'total_progress': 0.0})
for item in data_items:
    mod = item['module'] if item['module'] else '（未分类）'
    module_stats[mod]['count'] += 1
    module_stats[mod]['total_progress'] += item['progress']

# ============ 输出 ============
print('=' * 70)
print('   JUMP 6月台服OBT 测试进度分析报告')
print('   分析依据：仅看"测试进度"列百分比，忽略"测试状态"列')
print('=' * 70)

print(f'\n[总览] 需求总条目数：{total}')
print(f'[总览] 整体加权完成百分比：{avg_progress:.1f}%')

print(f'\n{"─" * 50}')
print(f'{"进度区间":<20s} {"数量":>5s} {"占比":>8s}')
print(f'{"─" * 50}')
for label, items in buckets.items():
    cnt = len(items)
    pct = cnt / total * 100 if total > 0 else 0
    bar = '█' * int(pct / 2)
    print(f'{label:<20s} {cnt:>5d} {pct:>7.1f}%  {bar}')
print(f'{"─" * 50}')

print(f'\n{"=" * 70}')
print('   按功能模块统计')
print(f'{"─" * 70}')
print(f'{"模块":<20s} {"条目数":>6s} {"平均进度":>10s}')
print(f'{"─" * 70}')
for mod in sorted(module_stats.keys(), key=lambda m: module_stats[m]['count'], reverse=True):
    s = module_stats[mod]
    avg = s['total_progress'] / s['count'] if s['count'] > 0 else 0
    print(f'{mod:<20s} {s["count"]:>6d} {avg:>9.1f}%')
print(f'{"─" * 70}')

# ============ 按测试负责人统计 ============
tester_stats = defaultdict(lambda: {'count': 0, 'total_progress': 0.0, 'items': []})
for item in data_items:
    t = item['tester'] if item['tester'] else '（未指定）'
    tester_stats[t]['count'] += 1
    tester_stats[t]['total_progress'] += item['progress']
    tester_stats[t]['items'].append(item)

print(f'\n{"=" * 70}')
print('   按测试负责人统计（仅看"测试进度"列百分比）')
print(f'{"─" * 85}')
print(f'{"测试负责人":<12s} {"总条目":>6s} {"100%":>6s} {"90-99":>6s} {"70-89":>6s} {"50-69":>6s} {"1-49":>6s} {"0%":>6s} {"整体进度":>10s}')
print(f'{"─" * 85}')
for t in sorted(tester_stats.keys(), key=lambda t: tester_stats[t]['count'], reverse=True):
    s = tester_stats[t]
    avg = s['total_progress'] / s['count'] if s['count'] > 0 else 0
    items = s['items']
    c100 = sum(1 for x in items if x['progress'] >= 100)
    c90  = sum(1 for x in items if 90 <= x['progress'] < 100)
    c70  = sum(1 for x in items if 70 <= x['progress'] < 90)
    c50  = sum(1 for x in items if 50 <= x['progress'] < 70)
    c1   = sum(1 for x in items if 0 < x['progress'] < 50)
    c0   = sum(1 for x in items if x['progress'] == 0)
    bar = '█' * int(avg / 5)
    print(f'{t:<12s} {s["count"]:>6d} {c100:>6d} {c90:>6d} {c70:>6d} {c50:>6d} {c1:>6d} {c0:>6d} {avg:>9.1f}%  {bar}')
print(f'{"─" * 85}')

print(f'\n   各负责人进度详情：')
print(f'{"─" * 70}')
for t in sorted(tester_stats.keys(), key=lambda t: tester_stats[t]['count'], reverse=True):
    s = tester_stats[t]
    avg = s['total_progress'] / s['count'] if s['count'] > 0 else 0
    print(f'\n  [{t}] 共 {s["count"]} 条，整体进度 {avg:.1f}%')
    for item in sorted(s['items'], key=lambda x: x['progress'], reverse=True):
        p_str = f'{item["progress"]:.0f}%' if item['progress'] > 0 else '--'
        print(f'    {p_str:>5s} | [{item["status"]}] | {item["module"]:<10s} | {item["detail"][:45]}' if item["module"] else f'    {p_str:>5s} | [{item["status"]}] | (子条目){">" * 3} {item["detail"][:35]}')
    print(f'    {"─" * 50}')

# 进度为 100% 的条目
print(f'\n{"=" * 70}')
print('   [完成] 进度 100%（已完成）的条目')
print(f'{"─" * 70}')
for item in buckets['100%（已完成）']:
    print(f'  Row{item["row"]:>4d} | {item["module"]:<12s} | {item["sub_feature"]:<12s} | {item["detail"][:45]}')

# 进度 90-99% 接近完成的条目
print(f'\n{"=" * 70}')
print('   [测试中] 进度 90%~99%（接近完成）的条目')
print(f'{"─" * 70}')
for item in buckets['90%～99%']:
    print(f'  Row{item["row"]:>4d} | {item["progress"]:>5.0f}% | [{item["status"]}] | {item["module"]:<12s} | {item["detail"][:45]}')

# 进度 70-89% 的条目
print(f'\n{"=" * 70}')
print('   [测试中] 进度 70%~89%（测试中后期）的条目')
print(f'{"─" * 70}')
for item in buckets['70%～89%']:
    print(f'  Row{item["row"]:>4d} | {item["progress"]:>5.0f}% | [{item["status"]}] | {item["module"]:<12s} | {item["detail"][:45]}')

# 进度 50-69% 的条目
print(f'\n{"=" * 70}')
print('   [测试中] 进度 50%~69%（测试中期）的条目')
print(f'{"─" * 70}')
for item in buckets['50%～69%']:
    print(f'  Row{item["row"]:>4d} | {item["progress"]:>5.0f}% | [{item["status"]}] | {item["module"]:<12s} | {item["detail"][:45]}')

# 0% 但状态为 "已完成" 或 "已转测" 的异常条目
print(f'\n{"=" * 70}')
print('   [警告] 异常标记：状态非"未转测"但进度为0%的条目（可能漏更新）')
print(f'{"─" * 70}')
anomaly_count = 0
for item in buckets['0%（未开始/无进度）']:
    if item['status'] in ('已完成', '已转测'):
        anomaly_count += 1
        print(f'  Row{item["row"]:>4d} | [{item["status"]}] | {item["module"]:<12s} | {item["detail"][:45]}')
if anomaly_count == 0:
    print('  （无异常）')
print(f'  共 {anomaly_count} 条可能漏更新进度')
