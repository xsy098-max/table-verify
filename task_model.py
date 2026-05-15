import json
import os

VERSION = "2.7.0"

AUTHOR = "奈叶摩尔"


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
    'extract_value': '📥 取值',
    'extract_grouped': '📊 分组取值',
    'split': '✂ 拆分',
    'flat_split': '📋 展平拆分',
    'lookup': '🔍 查表',
    'batch_lookup': '🔎 批量查表',
    'parse_drop': '🎁 解析掉落',
    'chain_lookup': '🔗 链式查找',
    'compare': '⚖ 比较',
    'item_mapping_compare': '🗺 道具映射比较',
}

BLOCK_DESCRIPTIONS = {
    'extract_value': '从表中取出一个值或一组值',
    'extract_grouped': '按条件分组取多行多列值(去重)',
    'split': '按分隔符拆分一个值为数组',
    'flat_split': '按多级分隔符展平拆分(如5_7|8_9→[5,7,8,9])',
    'lookup': '用一个值去另一张表查找对应字段',
    'batch_lookup': '对一组值逐个去另一张表查找',
    'parse_drop': '解析掉落格式数据(权重,道具ID,最小,最大)',
    'chain_lookup': '连续多步跨表查找',
    'compare': '比较期望值和实际值',
    'item_mapping_compare': '多列道具映射比较(一次比较多种道具)',
}

BLOCK_HELP = {
    'quick_start': {
        'title': '🚀 快速入门',
        'content': """\
对表工具使用指南
================

■ 对表工具是什么？

对表工具用来对比"设计表"和"配置表"中的数据是否一致。
比如：设计文档说青铜段位应该开放 A、B、C 三张地图，你需要检查配置表中是否真的配了这三张。


■ 工作流程

  1. 加载数据源 → 把 Excel 表格导入工具
  2. 搭建步骤   → 用积木块一步步取出、转换、对比数据
  3. 运行       → 点击运行，工具自动按步骤执行
  4. 看结果     → 查看每条对比是通过 ✅ 还是失败 ❌


■ 什么是"变量"？

变量就像给数据贴的一个"标签"。
每个步骤执行完后，可以把结果"保存为"一个变量（起个名字），
后续的步骤就可以用这个变量名来拿到前面的结果。

  步骤1：取值 → 保存为 "段位名"
  步骤2：分组取值 → 用 "段位名" 作为分组条件 → 保存为 "地图列表"
  步骤3：比较 → 用 "地图列表" 和 "配置表地图" 进行对比

就像流水线一样，每一步的输出是下一步的输入。


■ 预览按钮

每个步骤右边有一个「预览」按钮，点击后会执行到该步骤为止，
弹出窗口显示当前所有变量的值。这是调试的好帮手！


■ 一个完整的例子：检查排位赛地图配置

假设你要验证：配置表中的地图ID和设计文档中的地图名是否对应。

  步骤1 📥 取值：从配置表取出所有段位名
         → 保存为 "段位名"

  步骤2 📊 分组取值：在设计表中，按段位名分组取出地图名
         → 分组值变量选 "段位名"
         → 保存为 "设计表-地图名"

  步骤3 📥 取值：从配置表取出地图ID组
         → 保存为 "地图ID组"

  步骤4 📋 展平拆分：把 "5_7|34_35" 拆成 [5, 7, 34, 35]
         → 输入变量选 "地图ID组"
         → 标签变量选 "段位名"（保持按段位分组）
         → 保存为 "展平的地图ID"

  步骤5 🔎 批量查表：拿地图ID去地图表查地图名
         → 输入变量选 "展平的地图ID"
         → 保存为 "配置表-地图名"

  步骤6 ⚖ 比较：对比设计表地图名 vs 配置表地图名
         → 期望值选 "设计表-地图名"
         → 实际值选 "配置表-地图名"
         → 比较方式选 "集合匹配"（不要求顺序一致）


■ 常见问题

  Q: 步骤执行报错"变量 xxx 不存在"？
  A: 说明你引用了一个还没创建的变量。检查步骤顺序，
     确保引用的变量在之前的步骤中已经"保存为"。

  Q: 运行结果全是空的？
  A: 可能是取值范围或查找条件没配对。用「预览」按钮逐步检查。

  Q: 数据源加载失败？
  A: 检查文件路径和表名是否正确，确保 Excel 文件没被其他程序占用。
""",
    },
    'extract_value': {
        'title': '📥 取值',
        'content': """\
取值
====

■ 这是什么？

从表格中取出你需要的数据。
就像在 Excel 里用鼠标选中一块区域然后复制。


■ 两种取值方式

  ▸ 按范围：直接指定单元格范围，如 B2:B10
    适合：数据位置固定，知道在哪一列哪一行

  ▸ 按条件：在某一列中查找满足条件的行，取出对应列的值
    适合：数据位置不固定，需要根据条件筛选


■ 参数说明

  来源表（必填）
    选择从哪张表取数据。下拉框中会列出你在数据源中添加的所有表。

  取值方式（必填）
    • 按范围：填写单元格范围，格式和 Excel 一样，如 A1、B2:B10、C3:F3
    • 按条件：需要配合下面的查找列、查找值、返回列使用

  范围（按范围时必填）
    单元格范围，如：
    • B2  → 取一个格子
    • B2:B10 → 取 B 列第 2 到 10 行

  查找列（按条件时必填）
    在哪一列中查找，如 "段位"、"ID"。

  查找值（按条件时必填）
    要查找的具体值，如 "青铜"。

  返回列（按条件时，单列返回）
    找到行后，要取哪一列的值。

  多返回列（按条件时，多列返回）
    用逗号分隔多个列名，如 "地图1,地图2,地图3"。

  收集所有匹配行（按条件时，默认关闭）
    开启后，会把所有满足条件的行的值都收集起来（一个列表）。
    关闭时只取找到的第一行。

  保存为（必填）
    给取出来的数据起个名字（变量名），后续步骤用这个名字引用。


■ 举个例子

  场景：从配置表中取出所有段位名

  配置：
    来源表 = 排位赛配置表
    取值方式 = 按范围
    范围 = E4:E28
    保存为 = 段位名

  结果：
    段位名 = ['初战青铜Ⅲ', '初战青铜Ⅱ', '初战青铜Ⅰ', ...]


■ 小贴士

  • 如果范围只取到一个格子，结果会是一个单独的值（不是列表）
  • 如果取到多个格子，结果会是一个列表
  • 数字会自动识别为数字类型，不需要手动处理
  • 范围格式和 Excel 一样：字母代表列，数字代表行
""",
    },
    'extract_grouped': {
        'title': '📊 分组取值',
        'content': """\
分组取值
========

■ 这是什么？

按某个列的值进行分组，把每一组的多列数据收集起来（自动去重）。
就像在 Excel 里先按某一列筛选，然后把结果汇总。

比如：设计表中每个段位对应了多个地图名（分布在多行多列），
你想按段位把它们收集起来。


■ 输入是什么

  1. 一张已加载的表格
  2. 一个"分组值列表"（来自前面步骤的变量，如段位名列表）


■ 输出是什么

  一个字典（按分组归类）：
  {
    '初战青铜Ⅲ': ['短册街·树林', '界王星', '鲁斯凯那'],
    '初战青铜Ⅱ': ['短册街·树林', '界王星', '鲁斯凯那', '死亡森林'],
    ...
  }


■ 参数说明

  来源表（必填）
    选择从哪张表取数据。

  分组列（必填）
    按哪一列的值来分组，如 "段位"。

  分组值变量（必填）
    选择前面步骤保存的变量名（一个列表），工具会按列表中的每个值去查找。
    如选 "段位名"，工具就会依次查找段位=初战青铜Ⅲ、初战青铜Ⅱ 等等。

  返回列（必填）
    每组要取哪些列的值，用逗号分隔，如 "1,2,3,4,5,6,7"。

  跳过值（可选）
    要过滤掉的值，用逗号分隔。如填 "0" 会跳过值为 0 的格子。
    适用于表格中有占位值（如 0 表示"无"）的场景。

  向下填充空行（可选，默认关闭）
    开启后，如果分组列有空行，会自动继承上方的值。
    适用于设计表使用了合并单元格的场景：
    一个段位名合并了好几行，只有第一行写了段位名，下面的行为空。

  保存为（必填）
    给结果起个变量名。


■ 举个例子

  场景：从设计表中按段位取出所有地图名

  设计表内容：
    | 段位     | 1         | 2       | 3       |
    | 初战青铜Ⅲ | 短册街·树林 | 界王星   | 鲁斯凯那 |
    |           | 死亡森林   | 界王星   |         |

  配置：
    来源表 = 设计表
    分组列 = 段位
    分组值变量 = 段位名
    返回列 = 1,2,3
    向下填充空行 = 开启
    保存为 = 设计表-地图名

  结果：
    设计表-地图名 = {
      '初战青铜Ⅲ': ['短册街·树林', '界王星', '鲁斯凯那', '死亡森林']
    }


■ 小贴士

  • 结果会自动去重，同一个值不会出现两次
  • 如果设计表有合并单元格，记得开启「向下填充空行」
  • 「跳过值」可以过滤掉表格中的占位值
""",
    },
    'split': {
        'title': '✂ 拆分',
        'content': """\
拆分
====

■ 这是什么？

把一个字符串按分隔符拆成多个值。
就像把 "苹果,香蕉,橘子" 按逗号拆成三个水果。


■ 输入是什么

  一个变量（通常是前面步骤取出的一个字符串值）。

■ 输出是什么

  一个列表：
  "苹果,香蕉,橘子" → ["苹果", "香蕉", "橘子"]


■ 参数说明

  输入变量（必填）
    选择要拆分的变量名。

  分隔符（必填，默认 |）
    用什么符号来拆分。下拉框有常用选项，也可以自己输入。
    常见分隔符：|（竖线）、,（逗号）、_（下划线）

  保存为（必填）
    给结果起个变量名。


■ 举个例子

  输入变量 = 地图ID组，值是 "5,7,15,34"
  分隔符 = ,

  结果：[5, 7, 15, 34]


■ 小贴士

  • 拆分后的空值会保留为空字符串
  • 数字会自动识别为数字类型
  • 如果只需要一级分隔符，用这个就够了
  • 如果需要多级分隔符（如先按 | 再按 _），请用「展平拆分」
""",
    },
    'flat_split': {
        'title': '📋 展平拆分',
        'content': """\
展平拆分
========

■ 这是什么？

按多个分隔符逐级拆分，把嵌套结构展平成一个扁平列表。
是「拆分」的增强版，支持多级分隔符。

比如配置表中一个格子写了 "5_7|34_35"，你需要把它拆成 [5, 7, 34, 35]。


■ 和「拆分」的区别

  拆分：只用一个分隔符，"A|B|C" → ["A", "B", "C"]
  展平拆分：多个分隔符逐级拆，"5_7|8_9" → [5, 7, 8, 9]


■ 输入是什么

  一个变量。可以是：
  • 单个字符串，如 "5_7|34_35"
  • 字符串列表，如 ["5_7", "34_35|50_57"]


■ 输出是什么

  不填标签变量时（默认）：
    把所有值展平成一个列表
    → [5, 7, 34, 35, 50, 57]

  填了标签变量时：
    按标签分组，输出字典
    → {'初战青铜Ⅲ': [5, 7], '初战青铜Ⅱ': [34, 35, 50, 57]}


■ 参数说明

  输入变量（必填）
    选择要拆分的变量名。

  分隔符（必填，默认 |）
    按顺序写出所有分隔符，不用任何符号隔开。
    如填 "|_" 表示先按 | 拆，再按 _ 拆。

  标签变量（可选）
    如果填了，每个输入值会对应一个标签，输出按标签分组的字典。
    不填则输出扁平列表。
    典型场景：输入是每个段位的地图ID组，标签是段位名列表，
    这样拆分后仍然保持按段位分组。

  保存为（必填）
    给结果起个变量名。


■ 举个例子

  输入变量 = 地图ID组，值是 ["5_7", "34_35|50_57"]
  标签变量 = 段位名，值是 ["初战青铜Ⅲ", "初战青铜Ⅱ"]
  分隔符 = |_

  结果：
    {
      '初战青铜Ⅲ': [5, 7],
      '初战青铜Ⅱ': [34, 35, 50, 57]
    }


■ 小贴士

  • 分隔符是按顺序逐级拆分的：先按第1个拆，结果再按第2个拆，以此类推
  • 如果不需要分组，标签变量留空即可
  • 填了标签变量后，后续的「批量查表」和「比较」也能自动按分组处理
""",
    },
    'lookup': {
        'title': '🔍 查表',
        'content': """\
查表
====

■ 这是什么？

拿一个值去另一张表里查找，返回对应的字段值。
就像查字典：拿一个词去查它的释义。

比如：拿地图ID "15" 去地图表查它的地图名字。


■ 输入是什么

  一个变量（要查找的值）。


■ 输出是什么

  查到的那个字段的值（单个值）。
  如果找不到会报错。


■ 参数说明

  查找值（必填）
    选择要用来查找的变量名。

  目标表（必填）
    要在哪张表中查找。

  查找列（必填）
    在哪一列中查找匹配的值，如 "ID"。

  返回列（必填）
    找到匹配行后，要取哪一列的值，如 "地图名"。

  保存为（必填）
    给结果起个变量名。


■ 举个例子

  查找值 = 地图ID，值是 15
  目标表 = 游戏模式表
  查找列 = ID
  返回列 = 地图名字备注

  结果：保存为 = "短册街·树林"


■ 小贴士

  • 只会返回找到的第一行结果
  • 如果找不到匹配行，步骤会报错
  • 如果要查一组值（多个），请用「批量查表」
""",
    },
    'batch_lookup': {
        'title': '🔎 批量查表',
        'content': """\
批量查表
========

■ 这是什么？

「查表」的批量版本：对一组值逐个去另一张表查找对应字段。
就像一次性查很多个词的字典。

比如：拿一组地图ID [5, 7, 15] 去地图表查，得到 ["短册街·树林", "界王星", "鲁斯凯那"]。


■ 输入是什么

  一个变量，可以是：
  • 列表：[5, 7, 15] → 逐个查找，返回列表
  • 字典：{'青铜': [5, 7], '白银': [15, 34]} → 按分组查找，返回字典


■ 输出是什么

  列表输入 → 列表输出：
    [5, 7, 15] → ["短册街·树林", "界王星", "鲁斯凯那"]

  字典输入 → 字典输出：
    {'青铜': [5, 7]} → {'青铜': ["短册街·树林", "界王星"]}

  找不到的值会返回空字符串。


■ 参数说明

  输入数组（必填）
    选择要查找的变量名（一个列表或字典）。

  目标表（必填）
    要在哪张表中查找。

  查找列（必填）
    在哪一列中查找匹配的值。

  返回列（必填）
    找到匹配行后，要取哪一列的值。

  保存为（必填）
    给结果起个变量名。


■ 举个例子

  输入数组 = 展平的地图ID
  目标表 = 游戏模式表
  查找列 = ID
  返回列 = 地图名字备注

  结果：["短册街·树林", "界王星", "鲁斯凯那", "死亡森林"]


■ 小贴士

  • 找不到的值不会报错，而是返回空字符串
  • 如果输入是字典（分组结构），输出也会保持相同的分组结构
  • 这对后续「比较」按分组对比非常重要
""",
    },
    'parse_drop': {
        'title': '🎁 解析掉落',
        'content': """\
解析掉落
========

■ 这是什么？

解析游戏中的掉落配置数据。
配置表中的掉落格式通常是：权重,道具ID,最小数量,最大数量
这个积木块帮你把这些数据解析成结构化的信息。


■ 掉落格式说明

  单个掉落：权重,道具ID,最小数量,最大数量
  如：10000,20001,1,3 表示权重10000，道具20001，掉1-3个

  多个掉落用 | 分隔：
  10000,20001,1,3|5000,20002,1,1


■ 输入是什么

  一个变量（字符串或字符串列表）。


■ 输出是什么

  解析后的掉落列表：
  [
    {'weight': 10000, 'item_id': '20001', 'min': 1, 'max': 3},
    {'weight': 5000, 'item_id': '20002', 'min': 1, 'max': 1},
  ]


■ 参数说明

  输入变量（必填）
    选择要解析的掉落数据变量名。

  输入模式（必填，默认 数组）
    • 单个值：只解析一个掉落字符串
    • 数组：解析一组掉落字符串（每个对应一个关卡等级等）

  解析模式（必填，默认 只取必掉）
    • 只取必掉：只保留权重大于等于阈值的道具
    • 全部列出：保留所有道具

  必掉权重阈值（可选，默认 10000）
    权重达到多少算"必掉"。通常游戏设定 10000 = 100% 掉落。

  保存为（必填）
    给结果起个变量名。


■ 举个例子

  输入变量 = 掉落配置
  值 = ["10000,20001,1,3|5000,20002,1,1", "10000,20003,2,5"]

  配置：
    输入模式 = 数组
    解析模式 = 只取必掉
    阈值 = 10000

  结果：
    [
      [{'weight': 10000, 'item_id': '20001', 'min': 1, 'max': 3}],
      [{'weight': 10000, 'item_id': '20003', 'min': 2, 'max': 5}],
    ]
  （5000 权重的道具被过滤掉了）


■ 小贴士

  • 通常配合「道具映射比较」积木块一起使用
  • 阈值设为 0 等价于"全部列出"
  • 如果掉落格式是简单的 "道具ID,数量"，也能解析
""",
    },
    'chain_lookup': {
        'title': '🔗 链式查找',
        'content': """\
链式查找
========

■ 这是什么？

连续多步跨表查找，像接力赛一样：
先在 A 表查到值1 → 用值1去 B 表查到值2 → 用值2去 C 表查到值3...

比如：关卡ID → 奖励表查奖励ID → 道具表查道具名


■ 输入是什么

  一个变量（一个值或列表，作为查找的起始值）。


■ 输出是什么

  经过所有查找步骤后的最终值列表。


■ 参数说明

  输入变量（必填）
    起始查找值的变量名。

  查找链（必填）
    一系列查找步骤，每步包含：
    • 目标表：在哪张表查
    • 查找列：用哪一列匹配
    • 返回列：取哪一列的值作为下一步的输入

  保存为（必填）
    给结果起个变量名。


■ 举个例子

  查找链：
    第1步：在奖励表中，关卡ID列查到奖励ID列
    第2步：在道具表中，奖励ID列查到道具名列

  输入：[101, 102, 103]（关卡ID列表）

  结果：["金币", "经验药水", "钻石"]（道具名列表）


■ 小贴士

  • 每一步的输出自动成为下一步的输入
  • 找不到的值会变成空字符串，不会报错
  • 可以添加任意多步查找
""",
    },
    'compare': {
        'title': '⚖ 比较',
        'content': """\
比较
====

■ 这是什么？

对比"期望值"和"实际值"是否一致，生成通过 ✅ 或失败 ❌ 的结果。
这是验证流程的最后一步，也是最重要的步骤。


■ 输入是什么

  两个变量：
  • 期望值：设计文档中的数据（应该是什么）
  • 实际值：配置表中的数据（实际配了什么）


■ 输出是什么

  一系列比较结果，每条包含：
  • 标签：这一条是关于什么的
  • 期望值和实际值
  • 通过/失败状态
  • 说明（如果不一致，会告诉你差在哪里）


■ 参数说明

  期望值（必填）
    选择"应该是什么"的变量名。

  实际值（必填）
    选择"实际配了什么"的变量名。

  比较方式（必填，默认 逐项精确匹配）
    三种方式：

    ① 逐项精确匹配（exact_match）
      按顺序逐个对比，每个位置都要完全一样。
      适合：有序列表、单值对比。
      如：期望 [A, B, C]，实际 [A, B, C] → 通过
          期望 [A, B, C]，实际 [A, C, B] → 失败

    ② 包含匹配（contains）
      检查期望值是否出现在实际值中。
      适合：只要包含就行，不要求完全一致。
      如：期望 "地图A"，实际 "地图A,地图B" → 通过

    ③ 集合匹配（set_match）⭐ 推荐
      不要求顺序，只要两边包含相同的元素就算通过。
      适合：地图列表等不需要排序的数据。
      如：期望 [A, B, C]，实际 [C, A, B] → 通过 ✅
          期望 [A, B, C]，实际 [A, B, D] → 失败，提示缺少 C、多余 D

  行标签变量（可选）
    选择一个变量作为每条结果的标签。
    不填则自动编号"第1行、第2行..."。

  空值跳过（可选，默认关闭）
    开启后，如果期望值为空，这一条自动跳过（标记为通过）。
    适合某些段位不需要检查的场景。


■ 举个例子

  期望值 = 设计表-地图名（一个字典）
  实际值 = 配置表-地图名（一个字典）
  比较方式 = 集合匹配

  结果：
    初战青铜Ⅲ ✅ 集合匹配通过 (3个)
    初战青铜Ⅱ ❌ 缺少: ['死亡森林']; 多余: ['虚圈']


■ 小贴士

  • 如果两边都是字典（分组结构），会按分组名逐组对比
  • 集合匹配是最常用的方式，不要求顺序
  • 用「预览」按钮提前检查期望值和实际值，再选择比较方式
  • 比较结果可以双击查看完整详情
""",
    },
    'item_mapping_compare': {
        'title': '🗺 道具映射比较',
        'content': """\
道具映射比较
============

■ 这是什么？

专门用于对比道具掉落数量的高级比较积木块。
可以一次对比多种道具的掉落数量是否正确。

比如：检查每个关卡等级中，金币、经验、钻石的掉落数量是否和设计一致。


■ 和「比较」的区别

  「比较」：对比两个列表是否一致（通用）
  「道具映射比较」：专门对比道具掉落，可以分别检查多种道具


■ 输入是什么

  1. 掉落数据变量（来自「解析掉落」步骤）
  2. 映射关系（告诉工具每种道具的ID和对应的期望值变量）


■ 参数说明

  掉落数据来源（必填）
    选择「解析掉落」步骤保存的变量名。

  行标签变量（可选）
    每条结果的标签，如关卡等级名。

  映射关系（必填）
    配置要检查的道具，每项包含：
    • 名称：显示用的名称，如 "金币"
    • 道具ID：配置表中的道具ID
    • 期望值变量：选择包含期望数量的变量

  空值跳过（可选）
    开启后，期望为空的道具自动跳过。


■ 举个例子

  掉落数据 = [
    [{'weight': 10000, 'item_id': '20001', 'min': 100, 'max': 100}],
    [{'weight': 10000, 'item_id': '20001', 'min': 200, 'max': 200}],
  ]
  映射关系：名称=金币, 道具ID=20001, 期望值变量=期望金币数

  结果：
    第1级 ✅ 金币：期望 100, 实际 100
    第2级 ✅ 金币：期望 200, 实际 200


■ 小贴士

  • 通常流程：取值 → 解析掉落 → 取期望值 → 道具映射比较
  • 可以配置多个映射关系，一次检查多种道具
  • 如果掉落数量是范围（如 1-3），显示为 "1-3"
""",
    },
}

BLOCK_PARAMS = {
    'extract_value': [
        {'key': 'source', 'label': '来源表', 'type': 'datasource'},
        {'key': 'mode', 'label': '取值方式', 'type': 'choice', 'choices': ['range', 'condition'], 'choice_labels': ['按范围', '按条件']},
        {'key': 'range', 'label': '范围', 'type': 'text', 'condition': 'mode==range'},
        {'key': 'find_column', 'label': '查找列', 'type': 'column', 'condition': 'mode==condition'},
        {'key': 'find_value', 'label': '查找值', 'type': 'text', 'condition': 'mode==condition'},
        {'key': 'return_column', 'label': '返回列', 'type': 'column', 'condition': 'mode==condition'},
        {'key': 'return_columns', 'label': '多返回列', 'type': 'multi_column', 'condition': 'mode==condition'},
        {'key': 'collect_all', 'label': '收集所有匹配行', 'type': 'boolean', 'condition': 'mode==condition'},
        {'key': 'output_var', 'label': '保存为', 'type': 'text'},
    ],
    'extract_grouped': [
        {'key': 'source', 'label': '来源表', 'type': 'datasource'},
        {'key': 'find_column', 'label': '分组列', 'type': 'column'},
        {'key': 'find_values_var', 'label': '分组值变量', 'type': 'variable'},
        {'key': 'return_columns', 'label': '返回列', 'type': 'multi_column'},
        {'key': 'skip_values', 'label': '跳过值(逗号分隔)', 'type': 'text'},
        {'key': 'fill_down', 'label': '向下填充空行', 'type': 'boolean'},
        {'key': 'output_var', 'label': '保存为', 'type': 'text'},
    ],
    'split': [
        {'key': 'input_var', 'label': '输入变量', 'type': 'variable'},
        {'key': 'delimiter', 'label': '分隔符', 'type': 'choice', 'choices': ['|', ',', '_'], 'allow_custom': True},
        {'key': 'output_var', 'label': '保存为', 'type': 'text'},
    ],
    'flat_split': [
        {'key': 'input_var', 'label': '输入变量', 'type': 'variable'},
        {'key': 'delimiters', 'label': '分隔符(按顺序)', 'type': 'text'},
        {'key': 'label_var', 'label': '标签变量(可选)', 'type': 'variable'},
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
