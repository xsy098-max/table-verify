import json
import os

VERSION = "1.0.0"


class DataSource:
    def __init__(self, name, file_path, file_type=None, sheet_name=None, header_row=2):
        self.name = name
        self.file_path = file_path
        self.file_type = file_type or self._detect_type(file_path)
        self.sheet_name = sheet_name
        self.header_row = header_row

    @staticmethod
    def _detect_type(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            return 'csv'
        elif ext in ('.xlsx', '.xlsm'):
            return 'excel'
        return 'unknown'

    def to_dict(self):
        return {
            'name': self.name,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'sheet_name': self.sheet_name,
            'header_row': self.header_row,
        }

    @staticmethod
    def from_dict(d):
        return DataSource(
            name=d['name'],
            file_path=d['file_path'],
            file_type=d.get('file_type'),
            sheet_name=d.get('sheet_name'),
            header_row=d.get('header_row', 2),
        )


class BlockConfig:
    def __init__(self, block_type, params=None):
        self.block_type = block_type
        self.params = params or {}

    def to_dict(self):
        return {
            'type': self.block_type,
            'params': self.params,
        }

    @staticmethod
    def from_dict(d):
        return BlockConfig(
            block_type=d['type'],
            params=d.get('params', {}),
        )


class VerifyGroup:
    def __init__(self, name, steps=None):
        self.name = name
        self.steps = steps or []

    def to_dict(self):
        return {
            'name': self.name,
            'steps': [s.to_dict() for s in self.steps],
        }

    @staticmethod
    def from_dict(d):
        return VerifyGroup(
            name=d['name'],
            steps=[BlockConfig.from_dict(s) for s in d.get('steps', [])],
        )


class Task:
    def __init__(self, name='', data_sources=None, groups=None):
        self.name = name
        self.data_sources = data_sources or []
        self.groups = groups or []

    def to_dict(self):
        return {
            'version': VERSION,
            'task_name': self.name,
            'data_sources': [ds.to_dict() for ds in self.data_sources],
            'groups': [g.to_dict() for g in self.groups],
        }

    @staticmethod
    def from_dict(d):
        return Task(
            name=d.get('task_name', ''),
            data_sources=[DataSource.from_dict(ds) for ds in d.get('data_sources', [])],
            groups=[VerifyGroup.from_dict(g) for g in d.get('groups', [])],
        )

    def save(self, file_path):
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        task = Task.from_dict(data)
        return task


BLOCK_TYPES = {
    'extract_value': '取值',
    'split': '拆分',
    'lookup': '查表',
    'batch_lookup': '批量查表',
    'parse_drop': '解析掉落',
    'chain_lookup': '链式查找',
    'compare': '比较',
    'item_mapping_compare': '道具映射比较',
}

BLOCK_DESCRIPTIONS = {
    'extract_value': '从表中取出一个值或一组值',
    'split': '按分隔符拆分一个值为数组',
    'lookup': '用一个值去另一张表查找对应字段',
    'batch_lookup': '对一组值逐个去另一张表查找',
    'parse_drop': '解析掉落格式数据(权重,道具ID,最小,最大)',
    'chain_lookup': '连续多步跨表查找',
    'compare': '比较期望值和实际值',
    'item_mapping_compare': '多列道具映射比较(一次比较多种道具)',
}

BLOCK_PARAMS = {
    'extract_value': [
        {'key': 'source', 'label': '来源表', 'type': 'datasource'},
        {'key': 'mode', 'label': '取值方式', 'type': 'choice', 'choices': ['range', 'condition'], 'choice_labels': ['按范围', '按条件']},
        {'key': 'range', 'label': '范围', 'type': 'text', 'condition': 'mode==range'},
        {'key': 'find_column', 'label': '查找列', 'type': 'column', 'condition': 'mode==condition'},
        {'key': 'find_value', 'label': '查找值', 'type': 'text', 'condition': 'mode==condition'},
        {'key': 'return_column', 'label': '返回列', 'type': 'column', 'condition': 'mode==condition'},
        {'key': 'output_var', 'label': '保存为', 'type': 'text'},
    ],
    'split': [
        {'key': 'input_var', 'label': '输入变量', 'type': 'variable'},
        {'key': 'delimiter', 'label': '分隔符', 'type': 'choice', 'choices': ['|', ',', '_'], 'allow_custom': True},
        {'key': 'output_var', 'label': '保存为', 'type': 'text'},
    ],
    'lookup': [
        {'key': 'input_var', 'label': '查找值', 'type': 'variable'},
        {'key': 'target_table', 'label': '目标表', 'type': 'datasource'},
        {'key': 'find_column', 'label': '查找列', 'type': 'column'},
        {'key': 'return_column', 'label': '返回列', 'type': 'column'},
        {'key': 'output_var', 'label': '保存为', 'type': 'text'},
    ],
    'batch_lookup': [
        {'key': 'input_var', 'label': '输入数组', 'type': 'variable'},
        {'key': 'target_table', 'label': '目标表', 'type': 'datasource'},
        {'key': 'find_column', 'label': '查找列', 'type': 'column'},
        {'key': 'return_column', 'label': '返回列', 'type': 'column'},
        {'key': 'output_var', 'label': '保存为', 'type': 'text'},
    ],
    'parse_drop': [
        {'key': 'input_var', 'label': '输入变量', 'type': 'variable'},
        {'key': 'input_mode', 'label': '输入模式', 'type': 'choice', 'choices': ['single', 'array'], 'choice_labels': ['单个值', '数组']},
        {'key': 'parse_mode', 'label': '解析模式', 'type': 'choice', 'choices': ['must_drop', 'all'], 'choice_labels': ['只取必掉', '全部列出']},
        {'key': 'weight_threshold', 'label': '必掉权重阈值', 'type': 'text'},
        {'key': 'output_var', 'label': '保存为', 'type': 'text'},
    ],
    'chain_lookup': [
        {'key': 'input_var', 'label': '输入变量', 'type': 'variable'},
        {'key': 'chains', 'label': '查找链', 'type': 'chain_list'},
        {'key': 'output_var', 'label': '保存为', 'type': 'text'},
    ],
    'compare': [
        {'key': 'expected_var', 'label': '期望值', 'type': 'variable'},
        {'key': 'actual_var', 'label': '实际值', 'type': 'variable'},
        {'key': 'compare_mode', 'label': '比较方式', 'type': 'choice', 'choices': ['exact_match', 'contains', 'set_match'], 'choice_labels': ['逐项精确匹配', '包含匹配', '集合匹配']},
        {'key': 'label_var', 'label': '行标签变量', 'type': 'variable', 'optional': True},
        {'key': 'skip_empty', 'label': '空值跳过', 'type': 'boolean'},
    ],
    'item_mapping_compare': [
        {'key': 'drop_data_var', 'label': '掉落数据来源', 'type': 'variable'},
        {'key': 'label_var', 'label': '行标签变量', 'type': 'variable', 'optional': True},
        {'key': 'mappings', 'label': '映射关系', 'type': 'item_mappings'},
        {'key': 'skip_empty', 'label': '空值跳过', 'type': 'boolean'},
    ],
}
