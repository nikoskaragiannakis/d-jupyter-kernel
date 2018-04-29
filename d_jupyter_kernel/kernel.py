from contextlib import contextmanager
import os
import re
import shutil
import subprocess
import sys
import tempfile

from ipykernel.kernelbase import Kernel


__version__ = '1.0'


FUNC_PATTERN = re.compile(r"(\w+)\s+(\w+)\s*\((.*?)\)\s*\{(.*?)\}", re.S)
CLASS_PATTERN = re.compile(r"class (.*?)\s*\{(.*?)\}", re.S)
STRUCT_PATTERN = re.compile(r"struct (\w+)\s*\{(.*?)\}", re.S)
DECL_PATTERN = re.compile(r"^(\w+\s+)*(\w+)\s*\=\s*(.*)", re.MULTILINE)
IMPORT_PATTERN = re.compile(r"import\s+([\w+.,:= ]+);", re.S)


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
        self.buffer = {'imports': {}, 'funcs': {}, 'classes': {}, 'structs': {}, 'decls': {}}

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
        imports_str = ('\n'.join(list(self.buffer['imports'].values()))
                       if self.buffer['imports'] else '')
        funcs_str = ('\n'.join(list(self.buffer['funcs'].values()))
                     if self.buffer['funcs'] else '')
        classes_str = ('\n'.join(list(self.buffer['classes'].values()))
                       if self.buffer['classes'] else '')
        structs_str = ('\n'.join(list(self.buffer['structs'].values()))
                       if self.buffer['structs'] else '')
        decl_str = ('\n'.join(list(self.buffer['decls'].values()))
                    if self.buffer['decls'] else '')

        if any(re.match(pattern, code) for pattern in (IMPORT_PATTERN, FUNC_PATTERN,
                                                       CLASS_PATTERN, STRUCT_PATTERN,
                                                       DECL_PATTERN)):
            main_code = ''
        else:
            main_code = code
        main_str = "void main() {{{}}}".format(main_code)

        return '{}\n\n{}\n\n{}\n\n{}\n\n{}\n\n{}'.format(imports_str, classes_str, structs_str,
                                                         funcs_str, decl_str, main_str)

    def _execute_code(self, code):
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

    def _remove_added(self, added):
        for section in self.buffer:
            self.buffer[section] = {k: v
                                    for k, v in self.buffer[section].items()
                                    if k not in added[section]}

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=True):
        self._allow_stdin = allow_stdin
        added = {}
        if not silent:
            added['classes'] = self._get_classes(code)
            added['decls'] = self._get_decls(code)
            added['funcs'] = self._get_funcs(code)
            added['structs'] = self._get_structs(code)
            added['imports'] = self._get_imports(code)

            try:
                self._execute_code(code)
            except CompilationError:
                self._remove_added(added)
            finally:
                return {'status': 'ok', 'execution_count': self.execution_count,
                        'payload': [], 'user_expressions': {}}

    def do_complete(self, code, cursor_pos):
        # TODO: Implement this
        return super().do_complete(code, cursor_pos)

    def do_inspect(self, code, cursor_pos, detail_level=0):
        # TODO: Implement this
        return super().do_inspect(code, cursor_pos, detail_level=detail_level)

    def _get_classes(self, code):
        classes = re.findall(CLASS_PATTERN, code)
        added = set()
        for class_ in classes:
            name = class_[0].strip()
            if ':' in name:
                name, subclass = name.split(':')
            else:
                subclass = ''
            body = '{{{}}}'.format(class_[1])
            if subclass:
                res = ('class {}:{} {}'.format(name, subclass, body))
            else:
                res = ('class {} {}'.format(name, body))

            self.buffer['classes'][name] = res
            added.add(name)
        return added

    def _get_funcs(self, code):
        funcs = re.findall(FUNC_PATTERN, code)
        added = set()
        for func in funcs:
            type_ = func[0].strip()
            name = func[1].strip()
            params = '({})'.format(func[2])
            body = '{{{}}}'.format(func[3])
            res = ('{} {} {} {}'.format(type_, name, params, body))

            self.buffer['funcs'][name] = res
            added.add(name)
        return added

    def _get_structs(self, code):
        structs = re.findall(STRUCT_PATTERN, code)
        added = set()
        for struct in structs:
            name = struct[0].strip()
            body = '{{{}}}'.format(struct[1])
            res = ('{} {}'.format(name, body))

            self.buffer['structs'][name] = res
            added.add(name)
        return added

    def _get_decls(self, code):
        decls = re.findall(DECL_PATTERN, code)
        added = set()
        for decl in decls:
            type_ = decl[0].strip()
            name = decl[1].strip()
            value = decl[2]
            res = ('{}={}'.format(name, value))
            if type_:
                res = '{} {}'.format(type_, res)

            self.buffer['decls'][name] = res
            added.add(name)
        return added

    def _get_imports(self, code):
        imports = re.findall(IMPORT_PATTERN, code)
        added = set()
        for imp in imports:
            bases, *mods = imp.split(':')
            if mods:
                if '=' in base:
                    base, base_alias = bases.split('=')
                    base_str = '{} = {}'.format(base, base_alias)
                else:
                    base_str = base
                for mod in mods:
                    mod = mod.strip()
                    if '=' in mod:
                        mod, mod_alias = mod.split('=')
                        mod_str = '{} = {}'.format(mod, mod.alias)
                    else:
                        mod_str = mod
                    self.buffer['imports']['{}.{}'.format(base, mod)] = 'import {} : {};'.format(
                        base_str, mod_str)
                    added.add('{}.{}'.format(base, mod))
            else:
                for base in bases.split(','):
                    base = base.strip()
                    if '=' in base:
                        base, base_alias = base.split('=')
                        base_str = '{} = {}'.format(base, base_alias)
                    else:
                        base_str = base
                    self.buffer['imports'][base] = 'import {};'.format(base_str)
                    added.add(base)

        return added
