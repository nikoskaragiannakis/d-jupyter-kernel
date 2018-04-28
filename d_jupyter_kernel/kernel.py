from contextlib import contextmanager
import os
import re
import shutil
import subprocess
import sys
import tempfile

from ipykernel.kernelbase import Kernel


__version__ = '1.0'


class CompilationError(Exception):
    pass


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

    def __init__(self, **kwargs):
        self.buffer = {'imports': [], 'funcs': {}}

        self.func_def_pattern = re.compile(r"^\s*(\w+\s+)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*\{.*?",
                                           re.MULTILINE)
        self.import_pattern = re.compile(r"^import\s+[\w+.,: ]+;")

        super().__init__(**kwargs)

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

    def _output_code(self, code):
        imports_str = '\n'.join(self.buffer['imports']) if self.buffer['imports'] else ''
        funcs_str = '\n'.join(list(self.buffer['funcs'].values())) if self.buffer['funcs'] else ''
        main_str = "void main() {{{}}}".format(code)

        return '{}\n\n{}\n\n{}'.format(imports_str, funcs_str, main_str)

    def _execute_code(self, code, is_func=False, is_import=False):
        with tempdir() as temp_dir:
            with tempfile.NamedTemporaryFile(prefix='d_main_',
                                             suffix='.d',
                                             mode='w',
                                             dir=temp_dir) as d_file:
                d_file.write(self._output_code(code))
                d_file.flush()

                proc = subprocess.Popen(['dmd',
                                         d_file.name,
                                         '-op'],
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
                    raise CompilationError(stderr)

                exec_response = subprocess.Popen('{}'.format(d_file.name.split('.')[0]),
                                                 stdout=subprocess.PIPE,
                                                 stdin=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
                res = exec_response.communicate()
                self.send_response(self.iopub_socket, 'stream',
                                   {'name': 'stdout', 'text': res[0].decode('utf-8')})

                return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [],
                        'user_expressions': {}}

    @staticmethod
    def _clear_files(d_file_name):
        base_name = d_file_name.split('.')[0]
        os.remove('{}.o'.format(base_name))
        os.remove(base_name)

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=True):
        self._allow_stdin = allow_stdin
        if not silent:
                try:
                    self._execute_code(code)
                except CompilationError:
                    pass
                else:
                    if re.match(self.func_def_pattern, code):
                        func_name = re.findall(self.func_def_pattern, code)[0][1]
                        self.buffer['funcs'][func_name] = code
                    elif re.match(self.import_pattern, code):
                        self.buffer['imports'].append(code)
                finally:
                    return {'status': 'ok', 'execution_count': self.execution_count,
                            'payload': [], 'user_expressions': {}}

    def do_complete(self, code, cursor_pos):
        # TODO: Implement this
        return super().do_complete(code, cursor_pos)

    def do_inspect(self, code, cursor_pos, detail_level=0):
        # TODO: Implement this
        return super().do_inspect(code, cursor_pos, detail_level=detail_level)
