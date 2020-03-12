import click
from git import RemoteProgress


def op_code_to_label(op_code):
    if op_code == 33:
        return 'Receiving objects:'
    if op_code == 65:
        return 'Resolving deltas:'
    return ''


class GitProgressPrinter(RemoteProgress):
    progress = None

    def update(self, op_code, cur_count, max_count=100.0, message=''):
        if cur_count <= 1:
            self.progress = click.progressbar(length=int(max_count),
                                              label=op_code_to_label(op_code))
        self.progress.pos = cur_count
        self.progress.update(0)

        if cur_count == max_count:
            self.progress.render_finish()
