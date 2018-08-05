from contextlib import contextmanager
import os
import re
import shutil
import subprocess
import sys
import tempfile

from ipykernel.kernelbase import Kernel


__version__ = '1.0'


@contextmanager
def tempdir():
    path = tempfile.mkdtemp(dir=os.getcwd())
    try:
        yield path
    finally:
        try:
            shutil.rmtree(path)
        except IOError:
            sys.stderr.write('Failed to clean up temp dir {}'.format(path))


class DKernel(Kernel):
    implementation = 'd_kernel'
    language = 'd'
    language_info = {'name': 'd',
                     'mimetype': 'text/plain',
                     'file_extension': '.d'}

    @property
    def implementation_version(self):
        return __version__

    @property
    def language_version(self):
        m = re.search(r'(v\d+(\.\d+)+)',
                      subprocess.check_output(['dmd', '--version']).decode('utf-8'))
        return m.group(1)

    @property
    def banner(self):
        return "D kernel.\n " \
               "Uses dmd, compiles in D {}, and creates source code files and " \
               "executables in temporary folder.\n".format(self.language_version)

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=True):
        self._allow_stdin = allow_stdin
        if not silent:
            with tempdir() as temp_dir:
                with tempfile.NamedTemporaryFile(suffix='.d', mode='w', dir=temp_dir) as d_file:
                    d_file.write(code)
                    d_file.flush()
                    proc = subprocess.Popen(['dmd', d_file.name, '-op'],
                                            bufsize=0,
                                            cwd=temp_dir,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
                    stdout, stderr = proc.communicate()
                    if stderr:
                        rows = stderr.decode('utf-8').split('\n')
                        rows = [''.join(row.replace(d_file.name, 'line')) for row in rows]
                        stderr = '\n'.join(rows)
                        self.send_response(self.iopub_socket, 'stream',
                                           {'name': 'stdout', 'text': stderr})
                        return {'status': 'ok', 'execution_count': self.execution_count,
                                'payload': [], 'user_expressions': {}}

                    exec_response = subprocess.Popen('{}'.format(d_file.name.split('.')[0]),
                                                     stdout=subprocess.PIPE,
                                                     stdin=subprocess.PIPE,
                                                     stderr=subprocess.PIPE)
                    res = exec_response.communicate()
                    self.send_response(self.iopub_socket, 'stream',
                                       {'name': 'stdout', 'text': res[0].decode('utf-8')})

                    return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [],
                            'user_expressions': {}}

    def do_complete(self, code, cursor_pos):
        # TODO: Implement this
        return super().do_complete(code, cursor_pos)

    def do_inspect(self, code, cursor_pos, detail_level=0):
        # TODO: Implement this
        return super().do_inspect(code, cursor_pos, detail_level=detail_level)
