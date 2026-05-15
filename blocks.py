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
    if '_' in s:
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
        return_columns = params.get('return_columns', '')
        collect_all = params.get('collect_all', False)

        if not find_column:
            raise BlockError('取值', "未设置查找列")

        ret_cols = [c.strip() for c in return_columns.split(',') if c.strip()] if return_columns else [return_column]
        if not ret_cols or not ret_cols[0]:
            raise BlockError('取值', "未设置返回列")

        if collect_all:
            rows = table.find_rows(find_column, find_value)
            if not rows:
                raise BlockError('取值', f"在表 '{source_name}' 中未找到 {find_column}={find_value}")
            collected = []
            for row in rows:
                for col in ret_cols:
                    val = row.get(col, '')
                    if val and str(val).strip():
                        collected.append(_try_number(str(val).strip()))
            pool[output_var] = collected
        else:
            row = table.find_row(find_column, find_value)
            if row is None:
                raise BlockError('取值', f"在表 '{source_name}' 中未找到 {find_column}={find_value}")
            if len(ret_cols) == 1:
                value = row.get(ret_cols[0], '')
                pool[output_var] = _try_number(value)
            else:
                values = []
                for col in ret_cols:
                    val = row.get(col, '')
                    if val and str(val).strip():
                        values.append(_try_number(str(val).strip()))
                pool[output_var] = values
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


def _do_flat_split(value_str, delimiters):
    result = [str(value_str)]
    for d in delimiters:
        next_result = []
        for part in result:
            for p in part.split(d):
                p = p.strip()
                if p:
                    next_result.append(p)
        result = next_result
    return [_try_number(p) for p in result]


def execute_flat_split(params, pool, tables):
    input_var = params.get('input_var', '')
    delimiters = params.get('delimiters', '|_')
    output_var = params.get('output_var', '')
    label_var = params.get('label_var', '')

    if not input_var or not output_var:
        raise BlockError('展平拆分', "未设置输入变量或保存为")

    value = _get_var(pool, input_var, '展平拆分')
    labels = _get_var(pool, label_var, '展平拆分') if label_var else None

    if labels and isinstance(value, list):
        if isinstance(labels, str):
            labels = [labels]
        result = {}
        for i, item in enumerate(value):
            key = str(labels[i]) if i < len(labels) else str(i)
            result[key] = _do_flat_split(item, delimiters)
    elif isinstance(value, list):
        parts = []
        for item in value:
            parts.extend(_do_flat_split(item, delimiters))
        result = parts
    else:
        result = _do_flat_split(value, delimiters)

    pool[output_var] = result
    return result


def execute_extract_grouped(params, pool, tables):
    source = params.get('source', '')
    find_column = params.get('find_column', '')
    find_values_var = params.get('find_values_var', '')
    return_columns = params.get('return_columns', '')
    output_var = params.get('output_var', '')
    skip_values_str = params.get('skip_values', '')
    skip_values = set(v.strip() for v in skip_values_str.split(',') if v.strip())
    fill_down = params.get('fill_down', False)

    if not source or not find_column or not find_values_var or not return_columns or not output_var:
        raise BlockError('分组取值', "缺少必要参数")

    table = tables.get(source)
    if not table:
        raise BlockError('分组取值', f"未找到数据源: {source}")

    find_values = _get_var(pool, find_values_var, '分组取值')
    if isinstance(find_values, str):
        find_values = [find_values]

    ret_cols = [c.strip() for c in return_columns.split(',')]

    if fill_down:
        result = _extract_grouped_fill_down(table, find_column, find_values, ret_cols, skip_values)
    else:
        result = {}
        for val in find_values:
            key = str(val)
            rows = table.find_rows(find_column, key)
            collected = []
            for row in rows:
                for col in ret_cols:
                    cell_val = row.get(col, '')
                    stripped = str(cell_val).strip()
                    if stripped and stripped not in skip_values:
                        collected.append(stripped)
            seen = set()
            unique = []
            for item in collected:
                if item not in seen:
                    seen.add(item)
                    unique.append(item)
            result[key] = unique

    pool[output_var] = result
    return result


def _extract_grouped_fill_down(table, find_column, find_values, ret_cols, skip_values):
    find_values_set = set(str(v) for v in find_values)
    col_idx = None
    for ci, h in enumerate(table.headers):
        if str(h).strip() == find_column.strip():
            col_idx = ci
            break
    if col_idx is None:
        return {}

    result = {str(v): [] for v in find_values}
    current_group = ''

    for row_idx in range(table.header_row, len(table.raw_data)):
        row = table.raw_data[row_idx]
        cell_val = str(row[col_idx]).strip() if col_idx < len(row) else ''

        if cell_val:
            current_group = cell_val
        elif not current_group:
            continue

        if current_group not in find_values_set:
            if cell_val:
                current_group = ''
            continue

        for ci, col in enumerate(ret_cols):
            target_idx = None
            for hi, h in enumerate(table.headers):
                if str(h).strip() == col:
                    target_idx = hi
                    break
            if target_idx is None:
                continue
            val = str(row[target_idx]).strip() if target_idx < len(row) else ''
            if val and val not in skip_values:
                result[current_group].append(val)

    for key in result:
        seen = set()
        unique = []
        for item in result[key]:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        result[key] = unique

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

    if isinstance(values, dict):
        result = {}
        for key, val_list in values.items():
            if not isinstance(val_list, list):
                val_list = [val_list]
            looked = []
            for val in val_list:
                row = table.find_row(find_column, str(val))
                if row:
                    looked.append(row.get(return_column, ''))
                else:
                    looked.append('')
            result[key] = looked
        pool[output_var] = result
        return result

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

    if isinstance(expected, dict) and isinstance(actual, dict):
        return _compare_dicts(expected, actual, compare_mode, skip_empty)

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

        passed, msg = _compare_values(exp_str, act_str, compare_mode)
        details.append(CompareDetail(
            label=label, expected=exp, actual=act,
            passed=passed, skipped=False, message=msg
        ))

    return details


def _compare_values(exp_str, act_str, compare_mode):
    if compare_mode == 'exact_match':
        exp_num = _try_number(exp_str)
        act_num = _try_number(act_str)
        passed = (exp_num == act_num)
        msg = '' if passed else f"期望 {exp_str}, 实际 {act_str}"
    elif compare_mode == 'contains':
        passed = exp_str in str(act_str)
        msg = '' if passed else f"期望包含 '{exp_str}', 实际 '{act_str}'"
    elif compare_mode == 'set_match':
        exp_set = set(exp_str.split('|')) if exp_str else set()
        act_set = set(act_str.split('|')) if act_str else set()
        passed = exp_set == act_set
        msg = '' if passed else f"期望集合 {exp_set}, 实际集合 {act_set}"
    else:
        passed = exp_str == act_str
        msg = '' if passed else f"期望 {exp_str}, 实际 {act_str}"
    return passed, msg


def _compare_dicts(expected_dict, actual_dict, compare_mode, skip_empty):
    from runner import CompareDetail

    details = []
    all_keys = list(expected_dict.keys())
    for key in all_keys:
        exp_list = expected_dict.get(key, [])
        act_list = actual_dict.get(key, [])

        if not isinstance(exp_list, list):
            exp_list = [exp_list]
        if not isinstance(act_list, list):
            act_list = [act_list]

        if compare_mode == 'set_match':
            exp_set = set(str(v).strip() for v in exp_list if str(v).strip())
            act_set = set(str(v).strip() for v in act_list if str(v).strip())
            if skip_empty:
                exp_set.discard('')

            if exp_set == act_set:
                details.append(CompareDetail(
                    label=key, expected=sorted(exp_list, key=str),
                    actual=sorted(act_list, key=str),
                    passed=True, skipped=False,
                    message=f'集合匹配通过 ({len(exp_set)}个)'
                ))
            else:
                missing = exp_set - act_set
                extra = act_set - exp_set
                msg_parts = []
                if missing:
                    msg_parts.append(f"缺少: {sorted(missing)}")
                if extra:
                    msg_parts.append(f"多余: {sorted(extra)}")
                details.append(CompareDetail(
                    label=key, expected=sorted(exp_list, key=str),
                    actual=sorted(act_list, key=str),
                    passed=False, skipped=False,
                    message='; '.join(msg_parts)
                ))
            continue

        max_len = max(len(exp_list), len(act_list))
        for i in range(max_len):
            exp = exp_list[i] if i < len(exp_list) else ''
            act = act_list[i] if i < len(act_list) else ''

            exp_str = str(exp).strip() if exp is not None else ''
            act_str = str(act).strip() if act is not None else ''

            if skip_empty and not exp_str:
                details.append(CompareDetail(
                    label=key, expected=exp, actual=act,
                    passed=True, skipped=True, message='空值跳过'
                ))
                continue

            passed, msg = _compare_values(exp_str, act_str, compare_mode)
            details.append(CompareDetail(
                label=key, expected=exp, actual=act,
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
