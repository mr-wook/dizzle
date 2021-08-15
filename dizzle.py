#!/bin/env python3

"""Tools to build DSLs (domain specific languages) with;"""

if True:
    import re


class DynaFile():
    "Dynamic File processing (expandable) centered around Script/DSL support;"
    def __init__(self, fn, mode='r', **kwa):
        "use __nocomment_ or some other unlikely string if you don't want comment-stripping;"
        self._fn = fn
        self._mode = mode
        self._comment = kwa.get('comment', '#')
        self.include = self.insert_raw
        self._trim_line_no = 0
        ifd = open(fn, mode)
        if mode == 'r':
            self._ibuf = [ln.strip() for ln in ifd.readlines()]
            self._all_data = [ ]
            self._line_no = 0
            for i in range(len(self._ibuf)):
                self._all_data.append(( i + 1, self._ibuf[i] ))
            self._trimmed = self.trim(self._ibuf)
            return
        if mode in [ 'w', 'a' ]:
            self._obuf = [ ]
            return
        raise ValueError(f"Illegal IO mode {mode}")

    def __getitem__(self, i):
        if self._mode == 'r':
            return self._ibuf[i]
        if self._mode in [ 'w', 'a' ]:
            return self._obuf[i]
        raise ValueError(f"Illegal IO mode {mode}")

    def __iter__(self):
        if self._mode != 'r':
            raise RuntimeError("Iterating a DynaFile only works for read mode")
        while self._line_no < len(self):
            yield self[self._line_no]
            self._line_no += 1

    def __len__(self):
        if self._mode == 'r':
            return len(self._ibuf)
        if self._mode in [ 'w', 'a' ]:
            return len(self._obuf)

    def __str__(self):
        if self._mode == 'r':
            return "\n".join(self._ibuf)
        if self._mode in [ 'w', 'a']:
            return "\n".join(self._obuf)

    def append(self, txt):
        if self._mode == 'r':
            self._ibuf.append()
            return txt
        if self._mode in ['w', 'a']:
            self._obuf.append(txt)
            return txt
        raise ValueError(f"Illegal IO mode {self._mode}")

    def insert_raw(self, where, newdata):
        if self._mode == 'r':
            buf = self._ibuf
        elif self._mode in [ 'w', 'a' ]:
            buf = self._obuf
        else:
            raise ValueError(f"Illegal IO mode {self._mode}")
        processed = buf[:where]
        unprocessed = buf[where:]
        # Don't move self._line_no during this process, ibuf should only grow;
        if self._mode == 'a':
            self._ibuf = processed + newdata + unprocessed
            self._trimmed = self.trim(self._ibuf)
        else:
            self._obuf = processed + newdata + unprocessed
            self._trimmed = self.trim(self._obuf)
        return self._line_no

    def insert_trimmed(self, newdata, where = None, **kwa):
        drop = kwa.get('exclude_source_lines', 1)
        if where == None:
            where = self.trim_line_no
        processed = self.trimmed[:where]
        unprocessed = self.trimmed[where + drop:]
        self._trimmed = processed + newdata + unprocessed
        self._trim_line_no = where - 1 # The yield will skip the first included line w/o this;

    def pop_trimmed(self, where = 0):
        self._trimmed.pop(where)

    def save(self, fn = None):
        if not fn:
            fn = self._fn
        if self._mode == 'r':
            # This is a essentially copy command
            self._obuf = self._ibuf[:]
        ofd = open(fn, self._mode)
        ostr = str(self)
        ofd.write(ostr + '\n')

    def trim(self, ibuf):
        trim = [ ]
        ibuf = filter(None, ibuf) # Remove blank lines;
        for ln in ibuf:
            if ln.startswith(self._comment):
                continue
            if self._comment in ln:
                start = ln.index(self._comment)
                ln = ln[:start].strip()
                trim.append(ln)
                continue
            trim.append(ln.strip())
        ibuf = filter(None, ibuf) # Remove blank lines that resulted from <spaces><comment>stuff;
        return trim

    def trim_iter(self):
        while self._trim_line_no < len(self.trimmed):
            yield self.trimmed[self._trim_line_no]
            self._trim_line_no += 1

    @property
    def all(self):
        if self._mode == 'r':
            return self._ibuf
        if self._mode in [ 'w', 'a' ]:
            return self._obuf
        raise ValueError(f"Illegal IO mode {self._mode}")

    @property
    def current_text(self):
        if self._mode == 'r':
            return self._ibuf[self.index]
        if self._mode in [ 'w', 'a' ]:
            return self._obuf[self.index]
        raise ValueError(f"Illegal IO mode {mode}")

    @property
    def index(self):
        return self._line_no

    @property
    def trimmed(self):
        return self._trimmed
    
    @property
    def trim_line_no(self):
        return self._trim_line_no

    @property
    def where(self):
        return self._line_no

class Expander():
    "Variable expansion"
    def __init__(self, *dicts, **kwa):
        self._debug = kwa.get('debug', False)
        self._start = kwa.get('start', '{')
        self._end = kwa.get('end', '}')
        self.local_scope = self.innermost
        self.reset(*dicts)

    def __getitem__(self, k):
        for dict_ in self._locals_first:
            if k in dict_:
                return dict_[k]
        raise KeyError(f"No such key {k} in any known scope")

    def __contains__(self, k):
        for dict_ in self._locals_first:
            if k in dict_:
                return True
        return False

    def __setitem__(self, k, v):
        self.locals[k] = v

    # All the other expanding code goes here:
    def __call__(self, expr, **kwa):
        return self.expand(expr, **kwa)
        ## raise NotImplementedError

    def expand(self, text, **kwa):
        tokens = self.simple_tokenize(text, **kwa)
        expanded_tokens = self.expand_tokens(*tokens)
        return expanded_tokens

    def expand_tokens(self, *tokens, **kwa):
        expanded_tokens = [ ]
        default = kwa.get('default', None)
        for token in tokens:
            # Replace with if (self._start in token) and (self._end in token)
            #   when we support re.sub for multi-expands per token;
            if token.startswith(self._start) and token.endswith(self._end):
                varname = token[1:-1]
                # Get number of tokens in value if prefixed by "~"
                show_length = True if varname.startswith("~") else False
                if show_length:
                    varname = varname[1:]
                v = self.get(varname, None)
                if v != None:
                    if show_length:
                        if type(v) in [ type([]), type({}) ]:
                            v = str(len(v))
                        elif type(v) in [ type("") ]:
                            v = str(len(Expander.tokenize(v)))
                        else:
                            self._error = f"Can't process value of type {type(v)}"
                            return False
                    expanded_tokens.append(v)
                else:
                    if default:
                        expanded_tokens.append(default)
                        continue
                    ## bad_where, bad_ln = self._mf.trim_line_no, self._mf[self._mf.trim_line_no]
                    self._error = f"Unset variable {varname}"
                    return False
            else:
                expanded_tokens.append(token)
        return expanded_tokens

    def get(self, k, dflt = None):
        for dict_ in self._locals_first:
            if k in dict_:
                return dict_[k]
        return dflt

    def format(self, k):
        v = self[k]
        if ':' not in v:
            return v
        v_data, v_fmt = re.split(r'\s*:\s*', v, 1)
        v_data, v_fmt = v_data.strip(), v_fmt.strip()
        type_ = str
        if v_data.isdigit():
            type_ = int
        elif re.match(r'\d+\.\d*', v_data):
            type_ = float
        v_data = type_(v_data)
        return format(v_data, v_fmt)

    def innermost(self, k):
        dict_ = self._locals_first[0]
        if k in dict_:
            return dict_[k]
        raise KeyError(f"No such key {k} in innermost scope")

    def outermost(self, k):
        dict_ = self._globals_first[0]
        if k in dict_:
            return dict_[k]
        raise KeyError(f"No such key {k} in outermost scope")

    def reset(self, *dicts):
        "reset -- use for scope change (ie: new locals at end of list);"
        self._globals_first = list(dicts)
        self._locals_first = self._globals_first[:]
        self._locals_first.reverse()
        return self._globals_first

    def simple_tokenize(self, txt, **kwa):
        tokens = Expander.tokenize(txt, **kwa)
        return tokens

    @staticmethod
    def tokenize(txt, **kwa):
        translation = kwa.get('translation', None)
        pattern = kwa.get('pattern', r'\s+')
        rex = re.compile(pattern)
        tokens = rex.split(txt)
        if translation:
            translated_tokens = [ ]
            for token in tokens:
                token.replace(translation[0], translation[1])
                translated_tokens.append(token)
        else:
            return tokens
        return translated_tokens

    @property
    def error(self):
        return self._error
    
    @property
    def globals(self):
        return self._globals_first[0]

    @property
    def locals(self):
        return self._locals_first[0]

if __name__ == "__main__":
    "Test suite;"
    import sys

    def cli_get_args():
        args = sys.argv[:]
        pname = args.pop(0)
        return args

    def test_dynafile_include(include_fn):
        args = cli_get_args()
        include_fn = args.pop(0)
        df = DynaFile(include_fn)
        directives = [ ]
        for ln in df.trim_iter():
            tokens = re.split(r'\s+', ln)
            if tokens[0].lower() == 'include':
                sub_include_fn = tokens[1]
                sub_df = DynaFile(sub_include_fn)
                df.insert_trimmed(sub_df.trimmed)
            directives.append(ln)
        ostr = "\n".join(directives)
        print(ostr)
        return directives

    def test_dereferencer():
        globals_ = dict(ga="A", gb="B", gc="C", a="GA", b="BG", V="4:04")
        middles_ = dict(a="middle a", b="mid b", c="mid-c")
        locals_  = dict(a="a", b="b", c="c")
        xp = Expander(globals_, middles_, locals_)
        print(f"default a: {xp['a']}")
        print(f"innermost (most local) a: {xp.innermost('a')}")
        print(f"outermost (most global) a: {xp.outermost('a')}")
        print(f"default V: {xp['V']}")
        print(f"formatted V: {xp.format('V')}")


    def test_expand_file(src_fn):
        # >>> xp = Expander(global_dict, local_dict)
        #     s = xp("{foo}")
        #     s = xp("{foo}.{bar}")
        #     s = xp("{foo}.{frame:04d}.{ext}")
        globals_, locals_ = dict(), dict()
        xp = Expander(globals_, locals_)
        directives = test_dynafile_include(src_fn)
        # Now we have every legit directive, and can ignore (already processed) includes;
        for ln in directives:
            tokens = Expander.tokenize(ln)
            cmd = tokens.pop(0).lower()
            if cmd == 'include':
                continue
            if cmd == 'global':
                k, v = tokens
                xp.globals[k] = v
                continue
            if cmd == 'local':
                k, v = tokens
                xp.locals[k] = v
                continue
            if cmd == 'echo':
                olist = xp.expand_tokens(*tokens)
                print(" ".join(olist))
                continue
            print(f"Unknown command {cmd} in {ln}")
            continue
        return True

    def test_all(global_fn):
        # Test File Syntax:
        # global <varname> <stuff> -- add stuff to varname in global scope;
        # local <varname> <stuff> -- add stuff to varname in local scope;
        # include <filename> -- scan an included file at this point;
        # echo <stuff> -- echo stuff with expansions using default notation;
        args = cli_get_args()
        include_fn = args.pop(0)
        print(f"test_dynafile_include({include_fn})")
        directives = test_dynafile_include(include_fn)
        print("test_dereferencer()")
        test_dereferencer()
        print(f"test_expand_file({include_fn})")
        test_expand_file(include_fn)

    # Main
    test_all(None)
