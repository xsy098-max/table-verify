class BlockError(Exception):
    def __init__(self, block_type, message):
        self.block_type = block_type
        self.message = message
        super().__init__(f"[{block_type}] {message}")


def _get_source(tables, source_name):
    if source_name not in tables:
        raise BlockError('取值', f"数据源 '{source_name}' 不存在")
    return tables[source_name]


def _get_var(pool, var_name, block_type='未知'):
    if var_name not in pool:
        raise BlockError(block_type, f"变量 '{var_name}' 不存在")
    return pool[var_name]


def _try_number(val):
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    if not s:
        return val
    try:
        if '.' in s:
            return float(s)
        return int(s)
    except (ValueError, TypeError):
        return val


def execute_extract_value(params, pool, tables):
    source_name = params.get('source', '')
    mode = params.get('mode', 'range')
    output_var = params.get('output_var', '')
    if not output_var:
        raise BlockError('取值', "未设置'保存为'变量名")

    table = _get_source(tables, source_name)

    if mode == 'range':
        range_str = params.get('range', '')
        if not range_str:
            raise BlockError('取值', "未设置范围")
        values = table.get_range(range_str)
        values = [_try_number(v) for v in values]
        if len(values) == 1:
            pool[output_var] = values[0]
        else:
            pool[output_var] = values
    elif mode == 'condition':
        find_column = params.get('find_column', '')
        find_value = params.get('find_value', '')
        return_column = params.get('return_column', '')
        if not find_column or not return_column:
            raise BlockError('取值', "未设置查找列或返回列")

        row = table.find_row(find_column, find_value)
        if row is None:
            raise BlockError('取值', f"在表 '{source_name}' 中未找到 {find_column}={find_value}")

        value = row.get(return_column, '')
        pool[output_var] = _try_number(value)
    else:
        raise BlockError('取值', f"未知的取值方式: {mode}")

    return pool[output_var]


def execute_split(params, pool, tables):
    input_var = params.get('input_var', '')
    delimiter = params.get('delimiter', '|')
    output_var = params.get('output_var', '')

    if not input_var or not output_var:
        raise BlockError('拆分', "未设置输入变量或保存为")

    value = _get_var(pool, input_var, '拆分')
    raw = str(value)
    parts = raw.split(delimiter)
    result = []
    for p in parts:
        p = p.strip()
        if p:
            result.append(_try_number(p))
        else:
            result.append('')

    pool[output_var] = result
    return result


def execute_flat_split(params, pool, tables):
    input_var = params.get('input_var', '')
    delimiters = params.get('delimiters', '|_')
    output_var = params.get('output_var', '')

    if not input_var or not output_var:
        raise BlockError('展平拆分', "未设置输入变量或保存为")

    value = _get_var(pool, input_var, '展平拆分')
    raw = str(value)

    result = [raw]
    for d in delimiters:
        next_result = []
        for part in result:
            for p in str(part).split(d):
                p = p.strip()
                if p:
                    next_result.append(p)
        result = next_result

    result = [_try_number(p) for p in result]

    pool[output_var] = result
    return result


def execute_extract_grouped(params, pool, tables):
    source = params.get('source', '')
    find_column = params.get('find_column', '')
    find_values_var = params.get('find_values_var', '')
    return_columns = params.get('return_columns', '')
    output_var = params.get('output_var', '')

    if not source or not find_column or not find_values_var or not return_columns or not output_var:
        raise BlockError('分组取值', "缺少必要参数")

    table = tables.get(source)
    if not table:
        raise BlockError('分组取值', f"未找到数据源: {source}")

    find_values = _get_var(pool, find_values_var, '分组取值')
    if isinstance(find_values, str):
        find_values = [find_values]

    ret_cols = [c.strip() for c in return_columns.split(',')]

    result = {}
    for val in find_values:
        key = str(val)
        rows = table.find_rows(find_column, key)
        collected = []
        for row in rows:
            for col in ret_cols:
                cell_val = row.get(col, '')
                if cell_val and str(cell_val).strip():
                    collected.append(str(cell_val).strip())
        seen = set()
        unique = []
        for item in collected:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        result[key] = unique

    pool[output_var] = result
    return result


def execute_lookup(params, pool, tables):
    input_var = params.get('input_var', '')
    target_table = params.get('target_table', '')
    find_column = params.get('find_column', '')
    return_column = params.get('return_column', '')
    output_var = params.get('output_var', '')

    if not all([input_var, target_table, find_column, return_column, output_var]):
        raise BlockError('查表', "参数不完整")

    value = _get_var(pool, input_var, '查表')
    table = _get_source(tables, target_table)

    row = table.find_row(find_column, str(value))
    if row is None:
        raise BlockError('查表', f"在表 '{target_table}' 中未找到 {find_column}={value}")

    result = row.get(return_column, '')
    pool[output_var] = _try_number(result)
    return pool[output_var]


def execute_batch_lookup(params, pool, tables):
    input_var = params.get('input_var', '')
    target_table = params.get('target_table', '')
    find_column = params.get('find_column', '')
    return_column = params.get('return_column', '')
    output_var = params.get('output_var', '')

    if not all([input_var, target_table, find_column, return_column, output_var]):
        raise BlockError('批量查表', "参数不完整")

    values = _get_var(pool, input_var, '批量查表')
    table = _get_source(tables, target_table)

    if not isinstance(values, list):
        values = [values]

    results = []
    for val in values:
        row = table.find_row(find_column, str(val))
        if row:
            results.append(row.get(return_column, ''))
        else:
            results.append('')

    pool[output_var] = results
    return results


def execute_parse_drop(params, pool, tables):
    input_var = params.get('input_var', '')
    input_mode = params.get('input_mode', 'array')
    parse_mode = params.get('parse_mode', 'must_drop')
    weight_threshold = int(params.get('weight_threshold', 10000))
    output_var = params.get('output_var', '')

    if not input_var or not output_var:
        raise BlockError('解析掉落', "参数不完整")

    raw = _get_var(pool, input_var, '解析掉落')

    def parse_single(drop_str):
        drop_str = str(drop_str).strip()
        if not drop_str:
            return []
        items = []
        groups = drop_str.split('|') if '|' in drop_str else [drop_str]
        for group in groups:
            parts = group.split(',')
            if len(parts) >= 4:
                weight = int(parts[0].strip())
                item_id = parts[1].strip()
                min_val = int(parts[2].strip())
                max_val = int(parts[3].strip())
                items.append({
                    'weight': weight,
                    'item_id': item_id,
                    'min': min_val,
                    'max': max_val,
                })
            elif len(parts) == 2:
                items.append({
                    'weight': 10000,
                    'item_id': parts[0].strip(),
                    'min': int(parts[1].strip()),
                    'max': int(parts[1].strip()),
                })
        if parse_mode == 'must_drop':
            items = [i for i in items if i['weight'] >= weight_threshold]
        return items

    if input_mode == 'array':
        if not isinstance(raw, list):
            raw = [raw]
        results = [parse_single(v) for v in raw]
    else:
        results = parse_single(raw)

    pool[output_var] = results
    return results


def execute_chain_lookup(params, pool, tables):
    input_var = params.get('input_var', '')
    chains = params.get('chains', [])
    output_var = params.get('output_var', '')

    if not input_var or not chains or not output_var:
        raise BlockError('链式查找', "参数不完整")

    values = _get_var(pool, input_var, '链式查找')
    if not isinstance(values, list):
        values = [values]

    current_values = values
    for chain in chains:
        target_table = chain.get('target_table', '')
        find_column = chain.get('find_column', '')
        return_column = chain.get('return_column', '')

        if not all([target_table, find_column, return_column]):
            raise BlockError('链式查找', "查找链配置不完整")

        table = _get_source(tables, target_table)
        next_values = []
        for val in current_values:
            row = table.find_row(find_column, str(val))
            if row:
                next_values.append(row.get(return_column, ''))
            else:
                next_values.append('')
        current_values = next_values

    pool[output_var] = current_values
    return current_values


def execute_compare(params, pool, tables):
    from runner import CompareDetail

    expected_var = params.get('expected_var', '')
    actual_var = params.get('actual_var', '')
    compare_mode = params.get('compare_mode', 'exact_match')
    label_var = params.get('label_var', '')
    skip_empty = params.get('skip_empty', False)

    if not expected_var or not actual_var:
        raise BlockError('比较', "未设置期望值或实际值变量")

    expected = _get_var(pool, expected_var, '比较')
    actual = _get_var(pool, actual_var, '比较')
    labels = _get_var(pool, label_var, '比较') if label_var else None

    if not isinstance(expected, list):
        expected = [expected]
    if not isinstance(actual, list):
        actual = [actual]
    if labels and not isinstance(labels, list):
        labels = [labels]

    details = []
    max_len = max(len(expected), len(actual))
    for i in range(max_len):
        exp = expected[i] if i < len(expected) else ''
        act = actual[i] if i < len(actual) else ''
        label = str(labels[i]) if labels and i < len(labels) else f"第{i + 1}行"

        exp_str = str(exp).strip() if exp is not None else ''
        act_str = str(act).strip() if act is not None else ''

        if skip_empty and not exp_str:
            details.append(CompareDetail(
                label=label, expected=exp, actual=act,
                passed=True, skipped=True, message='空值跳过'
            ))
            continue

        if compare_mode == 'exact_match':
            exp_num = _try_number(exp_str)
            act_num = _try_number(act_str)
            passed = (exp_num == act_num)
            msg = '' if passed else f"期望 {exp_str}, 实际 {act_str}"
        elif compare_mode == 'contains':
            passed = exp_str in str(act)
            msg = '' if passed else f"期望包含 '{exp_str}', 实际 '{act_str}'"
        elif compare_mode == 'set_match':
            exp_set = set(exp_str.split('|')) if exp_str else set()
            act_set = set(act_str.split('|')) if act_str else set()
            passed = exp_set == act_set
            msg = '' if passed else f"期望集合 {exp_set}, 实际集合 {act_set}"
        else:
            passed = exp_str == act_str
            msg = '' if passed else f"期望 {exp_str}, 实际 {act_str}"

        details.append(CompareDetail(
            label=label, expected=exp, actual=act,
            passed=passed, skipped=False, message=msg
        ))

    return details


def execute_item_mapping_compare(params, pool, tables):
    from runner import CompareDetail

    drop_data_var = params.get('drop_data_var', '')
    label_var = params.get('label_var', '')
    mappings = params.get('mappings', [])
    skip_empty = params.get('skip_empty', False)

    if not drop_data_var or not mappings:
        raise BlockError('道具映射比较', "参数不完整")

    drop_data = _get_var(pool, drop_data_var, '道具映射比较')
    labels = _get_var(pool, label_var, '道具映射比较') if label_var else None

    if not isinstance(drop_data, list):
        drop_data = [drop_data]
    if labels and not isinstance(labels, list):
        labels = [labels]

    details = []
    for level_idx, level_items in enumerate(drop_data):
        level_label = str(labels[level_idx]) if labels and level_idx < len(labels) else f"第{level_idx + 1}级"

        if not isinstance(level_items, list):
            level_items = [level_items] if level_items else []

        for mapping in mappings:
            item_name = mapping.get('name', '')
            item_id = str(mapping.get('item_id', ''))
            expected_var = mapping.get('expected_var', '')

            expected_values = _get_var(pool, expected_var, '道具映射比较') if expected_var else []
            if not isinstance(expected_values, list):
                expected_values = [expected_values]

            exp_val = expected_values[level_idx] if level_idx < len(expected_values) else ''
            exp_str = str(exp_val).strip() if exp_val is not None else ''

            if skip_empty and not exp_str:
                details.append(CompareDetail(
                    label=level_label, expected=exp_val, actual='',
                    passed=True, skipped=True, message=f'{item_name} 空值跳过',
                    item_name=item_name
                ))
                continue

            actual_qty = 0
            found = False
            for item in level_items:
                if isinstance(item, dict) and str(item.get('item_id', '')) == item_id:
                    actual_qty = item.get('min', 0)
                    if item.get('min') != item.get('max'):
                        actual_qty = f"{item['min']}-{item['max']}"
                    found = True
                    break

            if not exp_str and not found:
                details.append(CompareDetail(
                    label=level_label, expected=exp_val, actual=actual_qty,
                    passed=True, skipped=True, message=f'{item_name} 双方均为空',
                    item_name=item_name
                ))
                continue

            exp_num = _try_number(exp_str)
            act_num = _try_number(str(actual_qty))
            passed = (exp_num == act_num)

            msg = ''
            if not passed:
                msg = f"{item_name}: 期望 {exp_str}, 实际 {actual_qty}"

            details.append(CompareDetail(
                label=level_label, expected=exp_val, actual=actual_qty,
                passed=passed, skipped=False, message=msg,
                item_name=item_name
            ))

    return details


EXECUTORS = {
    'extract_value': execute_extract_value,
    'split': execute_split,
    'flat_split': execute_flat_split,
    'extract_grouped': execute_extract_grouped,
    'lookup': execute_lookup,
    'batch_lookup': execute_batch_lookup,
    'parse_drop': execute_parse_drop,
    'chain_lookup': execute_chain_lookup,
    'compare': execute_compare,
    'item_mapping_compare': execute_item_mapping_compare,
}


def execute_block(block_type, params, pool, tables):
    executor = EXECUTORS.get(block_type)
    if not executor:
        raise BlockError(block_type, f"未知的积木块类型: {block_type}")
    return executor(params, pool, tables)
