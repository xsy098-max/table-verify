import unittest
import os
import json
import tempfile
import csv

from task_model import Task, DataSource, BlockConfig, VerifyGroup, VERSION, BLOCK_PARAMS
from table_loader import TableLoader, TableData, parse_range, col_letter_to_index, index_to_col_letter
from runner import Runner, RunResult, GroupResult, VariablePool
from blocks import execute_block, BlockError


class TestColConversion(unittest.TestCase):
    def test_col_letter_to_index(self):
        self.assertEqual(col_letter_to_index('A'), 0)
        self.assertEqual(col_letter_to_index('B'), 1)
        self.assertEqual(col_letter_to_index('Z'), 25)
        self.assertEqual(col_letter_to_index('AA'), 26)
        self.assertEqual(col_letter_to_index('AB'), 27)

    def test_index_to_col_letter(self):
        self.assertEqual(index_to_col_letter(0), 'A')
        self.assertEqual(index_to_col_letter(1), 'B')
        self.assertEqual(index_to_col_letter(25), 'Z')
        self.assertEqual(index_to_col_letter(26), 'AA')

    def test_roundtrip(self):
        for i in range(702):
            self.assertEqual(col_letter_to_index(index_to_col_letter(i)), i)


class TestParseRange(unittest.TestCase):
    def test_single_cell(self):
        self.assertEqual(parse_range('A1'), (0, 1, 0, 1))

    def test_range(self):
        self.assertEqual(parse_range('A1:C3'), (0, 1, 2, 3))

    def test_column_only(self):
        self.assertEqual(parse_range('E7:E56'), (4, 7, 4, 56))


class TestTableData(unittest.TestCase):
    def _make_table(self):
        table = TableData('test', 'test.csv')
        table.header_row = 1
        table.raw_data = [
            ['id', 'name', 'value'],
            ['1', 'apple', '100'],
            ['2', 'banana', '200'],
            ['3', 'cherry', '300'],
        ]
        table.headers = ['id', 'name', 'value']
        table.build_index()
        return table

    def test_get_range(self):
        table = self._make_table()
        result = table.get_range('A2:A4')
        self.assertEqual(result, ['1', '2', '3'])

    def test_get_range_2d(self):
        table = self._make_table()
        result = table.get_range_2d('A2:C3')
        self.assertEqual(result, [['1', 'apple', '100'], ['2', 'banana', '200']])

    def test_find_row(self):
        table = self._make_table()
        row = table.find_row('id', '2')
        self.assertEqual(row['name'], 'banana')
        self.assertEqual(row['value'], '200')

    def test_find_row_not_found(self):
        table = self._make_table()
        row = table.find_row('id', '999')
        self.assertIsNone(row)

    def test_find_rows(self):
        table = self._make_table()
        rows = table.find_rows('name', 'apple')
        self.assertEqual(len(rows), 1)

    def test_get_column_values(self):
        table = self._make_table()
        values = table.get_column_values('name')
        self.assertEqual(values, ['apple', 'banana', 'cherry'])


class TestCSVLoader(unittest.TestCase):
    def test_load_csv(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'value'])
            writer.writerow(['1', 'apple', '100'])
            writer.writerow(['2', 'banana', '200'])
            f.flush()
            path = f.name
        try:
            table = TableLoader.load(name='test', file_path=path, header_row=1)
            self.assertEqual(table.headers, ['id', 'name', 'value'])
            self.assertEqual(len(table.raw_data), 3)
            row = table.find_row('id', '1')
            self.assertEqual(row['name'], 'apple')
        finally:
            os.unlink(path)

    def test_load_csv_gbk(self):
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
            import codecs
            writer = codecs.getwriter('gbk')(f)
            writer.write('id,name\r\n')
            writer.write('1,苹果\r\n')
            f.flush()
            path = f.name
        try:
            table = TableLoader.load(name='test', file_path=path, header_row=1)
            self.assertEqual(table.headers, ['id', 'name'])
            row = table.find_row('id', '1')
            self.assertEqual(row['name'], '苹果')
        finally:
            os.unlink(path)


class TestVariablePool(unittest.TestCase):
    def test_set_get(self):
        pool = VariablePool()
        pool.set('x', 10)
        self.assertEqual(pool.get('x'), 10)

    def test_dict_syntax(self):
        pool = VariablePool()
        pool['x'] = [1, 2, 3]
        self.assertEqual(pool['x'], [1, 2, 3])
        self.assertTrue('x' in pool)
        self.assertFalse('y' in pool)

    def test_list_names(self):
        pool = VariablePool()
        pool.set('a', 1)
        pool.set('b', 2)
        self.assertEqual(sorted(pool.list_names()), ['a', 'b'])

    def test_clear(self):
        pool = VariablePool()
        pool.set('x', 1)
        pool.clear()
        self.assertIsNone(pool.get('x'))


class TestBlocks(unittest.TestCase):
    def _make_tables(self):
        bp = TableData('BattlePass', 'bp.csv')
        bp.header_row = 1
        bp.raw_data = [
            ['level', 'drop_id', 'exp_item1', 'exp_item2'],
            ['1', 'drop_001', '100', '50'],
            ['2', 'drop_002', '200', '0'],
            ['3', 'drop_003', '300', '75'],
        ]
        bp.headers = ['level', 'drop_id', 'exp_item1', 'exp_item2']
        bp.build_index()

        dm = TableData('DropMain', 'dm.csv')
        dm.header_row = 1
        dm.raw_data = [
            ['id', 'drop_sub_ids'],
            ['drop_001', '1001,1002'],
            ['drop_002', '1001,1003'],
            ['drop_003', '1002,1004'],
        ]
        dm.headers = ['id', 'drop_sub_ids']
        dm.build_index()

        return {'BattlePass': bp, 'DropMain': dm}

    def test_extract_value_range(self):
        tables = self._make_tables()
        pool = VariablePool()
        execute_block('extract_value', {
            'source': 'BattlePass',
            'mode': 'range',
            'range': 'A2:A4',
            'output_var': 'levels',
        }, pool, tables)
        self.assertEqual(pool['levels'], [1, 2, 3])

    def test_extract_value_condition(self):
        tables = self._make_tables()
        pool = VariablePool()
        execute_block('extract_value', {
            'source': 'BattlePass',
            'mode': 'condition',
            'find_column': 'level',
            'find_value': '2',
            'return_column': 'drop_id',
            'output_var': 'did',
        }, pool, tables)
        self.assertEqual(pool['did'], 'drop_002')

    def test_split(self):
        pool = VariablePool()
        pool['raw'] = '1001,1002,1003'
        result = execute_block('split', {
            'input_var': 'raw',
            'delimiter': ',',
            'output_var': 'parts',
        }, pool, {})
        self.assertEqual(result, [1001, 1002, 1003])
        self.assertEqual(pool['parts'], [1001, 1002, 1003])

    def test_flat_split(self):
        pool = VariablePool()
        pool['raw'] = '5_7_15|34_35_36'
        result = execute_block('flat_split', {
            'input_var': 'raw',
            'delimiters': '|_',
            'output_var': 'ids',
        }, pool, {})
        self.assertEqual(result, [5, 7, 15, 34, 35, 36])

    def test_flat_split_single(self):
        pool = VariablePool()
        pool['raw'] = '5_7_15'
        result = execute_block('flat_split', {
            'input_var': 'raw',
            'delimiters': '|_',
            'output_var': 'ids',
        }, pool, {})
        self.assertEqual(result, [5, 7, 15])

    def test_lookup(self):
        tables = self._make_tables()
        pool = VariablePool()
        pool['did'] = 'drop_002'
        execute_block('lookup', {
            'input_var': 'did',
            'target_table': 'DropMain',
            'find_column': 'id',
            'return_column': 'drop_sub_ids',
            'output_var': 'sub_ids',
        }, pool, tables)
        self.assertEqual(pool['sub_ids'], '1001,1003')

    def test_batch_lookup(self):
        tables = self._make_tables()
        pool = VariablePool()
        pool['ids'] = ['drop_001', 'drop_003']
        result = execute_block('batch_lookup', {
            'input_var': 'ids',
            'target_table': 'DropMain',
            'find_column': 'id',
            'return_column': 'drop_sub_ids',
            'output_var': 'sub_values',
        }, pool, tables)
        self.assertEqual(result, ['1001,1002', '1002,1004'])

    def test_parse_drop(self):
        pool = VariablePool()
        pool['raw'] = ['10000,2001,10,20', '5000,2002,5,5']
        result = execute_block('parse_drop', {
            'input_var': 'raw',
            'input_mode': 'array',
            'parse_mode': 'must_drop',
            'weight_threshold': '10000',
            'output_var': 'drops',
        }, pool, {})
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 1)
        self.assertEqual(result[0][0]['item_id'], '2001')
        self.assertEqual(len(result[1]), 0)

    def test_chain_lookup(self):
        tables = self._make_tables()
        pool = VariablePool()
        pool['levels'] = ['1', '2']
        result = execute_block('chain_lookup', {
            'input_var': 'levels',
            'chains': [
                {'target_table': 'BattlePass', 'find_column': 'level', 'return_column': 'drop_id'},
                {'target_table': 'DropMain', 'find_column': 'id', 'return_column': 'drop_sub_ids'},
            ],
            'output_var': 'chain_result',
        }, pool, tables)
        self.assertEqual(result, ['1001,1002', '1001,1003'])

    def test_compare_exact_match(self):
        pool = VariablePool()
        pool['expected'] = [100, 200, 300]
        pool['actual'] = [100, 200, 300]
        pool['labels'] = ['lv1', 'lv2', 'lv3']
        details = execute_block('compare', {
            'expected_var': 'expected',
            'actual_var': 'actual',
            'compare_mode': 'exact_match',
            'label_var': 'labels',
        }, pool, {})
        self.assertTrue(all(d.passed for d in details))

    def test_compare_fail(self):
        pool = VariablePool()
        pool['expected'] = [100]
        pool['actual'] = [200]
        details = execute_block('compare', {
            'expected_var': 'expected',
            'actual_var': 'actual',
            'compare_mode': 'exact_match',
        }, pool, {})
        self.assertFalse(details[0].passed)
        self.assertIn('200', details[0].message)

    def test_compare_skip_empty(self):
        pool = VariablePool()
        pool['expected'] = [100, '', 300]
        pool['actual'] = [100, 200, 300]
        details = execute_block('compare', {
            'expected_var': 'expected',
            'actual_var': 'actual',
            'compare_mode': 'exact_match',
            'skip_empty': True,
        }, pool, {})
        self.assertTrue(details[0].passed)
        self.assertTrue(details[1].skipped)
        self.assertTrue(details[2].passed)

    def test_item_mapping_compare(self):
        pool = VariablePool()
        pool['drops'] = [
            [{'weight': 10000, 'item_id': '1001', 'min': 100, 'max': 100}],
            [{'weight': 10000, 'item_id': '1001', 'min': 200, 'max': 200}],
        ]
        pool['exp'] = [100, 200]
        pool['levels'] = ['lv1', 'lv2']
        details = execute_block('item_mapping_compare', {
            'drop_data_var': 'drops',
            'label_var': 'levels',
            'mappings': [
                {'name': '经验', 'item_id': '1001', 'expected_var': 'exp'},
            ],
        }, pool, {})
        self.assertTrue(all(d.passed for d in details))
        self.assertEqual(details[0].label, 'lv1')
        self.assertEqual(details[1].label, 'lv2')


class TestRunner(unittest.TestCase):
    def _make_task_with_csv(self):
        tmpdir = tempfile.mkdtemp()
        csv_path = os.path.join(tmpdir, 'test.csv')
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'value'])
            writer.writerow(['1', 'apple', '100'])
            writer.writerow(['2', 'banana', '200'])
        task = Task(name='test_task')
        task.data_sources.append(DataSource(name='test', file_path=csv_path))
        group = VerifyGroup(name='g1')
        group.steps.append(BlockConfig(block_type='extract_value', params={
            'source': 'test', 'mode': 'range', 'range': 'C2:C3', 'output_var': 'vals',
        }))
        group.steps.append(BlockConfig(block_type='compare', params={
            'expected_var': 'vals', 'actual_var': 'vals',
            'compare_mode': 'exact_match',
        }))
        task.groups.append(group)
        return task, tmpdir

    def test_runner_basic(self):
        task, tmpdir = self._make_task_with_csv()
        try:
            runner = Runner()
            result = runner.run(task)
            self.assertEqual(result.task_name, 'test_task')
            self.assertEqual(len(result.group_results), 1)
            gr = result.group_results[0]
            self.assertIsNone(gr.error)
            self.assertTrue(gr.is_passed)
        finally:
            import shutil
            shutil.rmtree(tmpdir)

    def test_runner_skip_load(self):
        task, tmpdir = self._make_task_with_csv()
        try:
            table = TableLoader.load(name='test', file_path=task.data_sources[0].file_path, header_row=1)
            runner = Runner()
            runner.tables['test'] = table
            result = runner.run(task, skip_load=True)
            self.assertTrue(result.is_all_passed)
        finally:
            import shutil
            shutil.rmtree(tmpdir)


class TestTaskModel(unittest.TestCase):
    def test_serialization(self):
        task = Task(name='test')
        task.data_sources.append(DataSource(name='ds1', file_path='/tmp/test.csv'))
        group = VerifyGroup(name='g1')
        group.steps.append(BlockConfig(block_type='extract_value', params={
            'source': 'ds1', 'mode': 'range', 'range': 'A1:A5', 'output_var': 'x',
        }))
        task.groups.append(group)

        d = task.to_dict()
        self.assertEqual(d['task_name'], 'test')
        self.assertEqual(len(d['data_sources']), 1)
        self.assertEqual(len(d['groups']), 1)

        task2 = Task.from_dict(d)
        self.assertEqual(task2.name, 'test')
        self.assertEqual(len(task2.data_sources), 1)
        self.assertEqual(len(task2.groups), 1)
        self.assertEqual(task2.groups[0].steps[0].block_type, 'extract_value')

    def test_save_load(self):
        with tempfile.NamedTemporaryFile(suffix='.task', delete=False, mode='w') as f:
            path = f.name
        try:
            task = Task(name='save_test')
            task.save(path)
            task2 = Task.load(path)
            self.assertEqual(task2.name, 'save_test')
        finally:
            os.unlink(path)

    def test_version_exists(self):
        self.assertTrue(VERSION)
        parts = VERSION.split('.')
        self.assertEqual(len(parts), 3)

    def test_block_params_complete(self):
        for btype in ['extract_value', 'split', 'lookup', 'batch_lookup', 'parse_drop', 'chain_lookup', 'compare', 'item_mapping_compare']:
            self.assertIn(btype, BLOCK_PARAMS, f"Missing BLOCK_PARAMS for {btype}")
            params = BLOCK_PARAMS[btype]
            has_output = any(p['key'] == 'output_var' for p in params)
            if btype not in ('compare', 'item_mapping_compare'):
                self.assertTrue(has_output, f"{btype} missing output_var")


if __name__ == '__main__':
    unittest.main()
