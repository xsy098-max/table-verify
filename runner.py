from table_loader import TableLoader
from task_model import Task, BlockConfig
from blocks import execute_block, BlockError


class CompareDetail:
    __slots__ = ('label', 'expected', 'actual', 'passed', 'skipped', 'message', 'item_name')

    def __init__(self, label, expected, actual, passed, skipped=False, message='', item_name=''):
        self.label = label
        self.expected = expected
        self.actual = actual
        self.passed = passed
        self.skipped = skipped
        self.message = message
        self.item_name = item_name


class GroupResult:
    def __init__(self, group_name):
        self.group_name = group_name
        self.details = []
        self.error = None
        self.step_outputs = {}

    @property
    def passed_count(self):
        return sum(1 for d in self.details if d.passed and not d.skipped)

    @property
    def failed_count(self):
        return sum(1 for d in self.details if not d.passed)

    @property
    def skipped_count(self):
        return sum(1 for d in self.details if d.skipped)

    @property
    def total_count(self):
        return len(self.details)

    @property
    def is_passed(self):
        return self.failed_count == 0 and self.error is None


class RunResult:
    def __init__(self, task_name):
        self.task_name = task_name
        self.group_results = []

    @property
    def total_passed(self):
        return sum(g.passed_count for g in self.group_results)

    @property
    def total_failed(self):
        return sum(g.failed_count for g in self.group_results)

    @property
    def total_skipped(self):
        return sum(g.skipped_count for g in self.group_results)

    @property
    def is_all_passed(self):
        return all(g.is_passed for g in self.group_results)


class VariablePool:
    def __init__(self):
        self._vars = {}

    def set(self, name, value):
        self._vars[name] = value

    def get(self, name):
        return self._vars.get(name)

    def has(self, name):
        return name in self._vars

    def list_names(self):
        return list(self._vars.keys())

    def clear(self):
        self._vars.clear()

    def __setitem__(self, name, value):
        self._vars[name] = value

    def __getitem__(self, name):
        return self._vars[name]

    def __contains__(self, name):
        return name in self._vars


class Runner:
    def __init__(self):
        self.tables = {}

    def load_tables(self, data_sources):
        self.tables.clear()
        errors = []
        for ds in data_sources:
            try:
                table = TableLoader.load(
                    name=ds.name,
                    file_path=ds.file_path,
                    sheet_name=ds.sheet_name,
                    header_row=ds.header_row,
                )
                self.tables[ds.name] = table
            except Exception as e:
                errors.append(f"加载数据源 '{ds.name}' 失败: {e}")
        return errors

    def run(self, task, skip_load=False):
        if not skip_load:
            errors = self.load_tables(task.data_sources)
            if errors:
                result = RunResult(task.name)
                for err in errors:
                    gr = GroupResult("加载错误")
                    gr.error = err
                    result.group_results.append(gr)
                return result

        result = RunResult(task.name)

        for group in task.groups:
            pool = VariablePool()
            gr = GroupResult(group.name)
            result.group_results.append(gr)

            for step_idx, step in enumerate(group.steps):
                try:
                    block_result = execute_block(
                        step.block_type, step.params, pool, self.tables
                    )
                    gr.step_outputs[step_idx] = block_result

                    if isinstance(block_result, list) and block_result and isinstance(block_result[0], CompareDetail):
                        gr.details.extend(block_result)

                except BlockError as e:
                    gr.error = f"步骤{step_idx + 1} ({step.block_type}): {e.message}"
                    break
                except Exception as e:
                    gr.error = f"步骤{step_idx + 1} ({step.block_type}): {e}"
                    break

        return result
