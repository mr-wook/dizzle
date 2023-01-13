#!/bin/env python3.10

"""Tools to build DSLs (domain specific languages) with;"""

if True:
    import os
    import re
    import shlex
    import sys
    from   typing import Any, AnyStr, Dict, List, Match, NoReturn, Pattern


class DynaFile():
    "Dynamic File processing (expandable) centered around Script/DSL support;"
    def __init__(self, fn, mode='r', **kwa):
        "use __nocomment_ or some other unlikely string if you don't want comment-stripping;"
        self._fn = fn
        self._mode = mode
        self._comment = kwa.get('comment', '#')
        self._continuation = kwa.get('continuation', None)
        default_search_dirs = [ '.', '~', '/etc/dlvdsl' ]
        search_dirs = kwa.get('search_dirs', default_search_dirs)
        self._search_dirs = [os.path.expanduser(dirnm) for dirnm in search_dirs]
        self.include = self.insert_raw
        self._trim_line_no = 0
        # fd = self._open(fn, mode)
        ifd = open(fn, mode)
        if mode == 'r':
            self._read_file(fn)
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

    def _open(self, fn, mode):
        if mode == 'r':
            if not os.path.isfile(fn):
                if '/' in fn:
                    # Path specified, shouldn't search along search_dirs;
                    return False
                fn = self._search(fn)
                if fn == False:
                    return False
            fd = open(fn, mode)
            return fd
        return True # Always true for other modes...until rb is implemented;

    def pop_trimmed(self, where = 0):
        self._trimmed.pop(where)

    def _read_file(self, fn):
        ifd = open(fn, 'r')
        self._ibuf = [ln.strip() for ln in ifd.readlines()]
        ifd.close()
        self._all_data = [ ]
        self._line_no = 0
        nlines = len(self._ibuf)
        i = 0
        while i < nlines:
            ln = self._ibuf[i]
            if self._continuation:
                if ln.endswith(self._continuation):
                    done = False
                    offset = 1
                    while not done:
                        if i + offset >= nlines:
                            raise EOFError(f"Continuation symbol appears immediately before EOF in {fn}")
                        ln = ln[:-len(self._continuation)] # Strip off the continuation character;
                        ln = ln + self._ibuf[i + offset]
                        offset += 1
                        if not ln.endswith(self._continuation):
                            done = True
                            continue
                    i = i + offset - 1
            i += 1
            self._all_data.append(( i, ln ))
        self._trimmed = self.trim(self._ibuf)

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
        # Replace with dataflow generator approach (cf. mcoding:python generators)?
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


class VarHelper():
    def __init__(self, name: AnyStr, base_pattern: AnyStr, start: AnyStr = "{", end: AnyStr = "}") -> NoReturn:
        self._name = name
        self._groupdict = dict()
        self._groups = [ ]
        # self._dict = dict(matcher=None, matched=None, varname=None, value=None, full=None, core=None)
        self._base = base_pattern
        # print("base", base_pattern)
        self._start_len, self._end_len = len(start), len(end)
        self._start, self._end = start, end
        core_pattern = self._core_pattern = rf'(?P<core>{base_pattern})'
        # print("core", self._core_pattern)
        self._core_rex = re.compile(self._core_pattern)
        full_pattern = rf'(?P<full>{start}\s*{core_pattern}\s*{end})'
        self._full_pattern = full_pattern
        self._full_rex = re.compile(full_pattern)
        # print("full", full_pattern)
        self._core = self._full = None
        return

    def __contains__(self, k):
        return k in self._groupdict

    def __getitem__(self, k):
        if type(k) == type(0):
            return self._groups[k]
        if type(k) == type(""):
            return self._groupdict[k]

    def __str__(self):
        return f"{self._name}: {str(self._full)}"

    def findall(self, token: AnyStr) -> List:
        """Uses the full pattern (includes delimiters) to find all matches in token;"""
        matches = self._full_rex.findall(token) # findall returns a list of tuples of matches
        self._matches = [ mtch for mtch in matches ] # Prune it to lists of [ full, core ], for easy replace operations;
        return self._matches

    def match(self, token: AnyStr) -> Match[str]:
        """Uses the core pattern to extract ONLY the variable name"""
        mtch = self._core_rex.match(token)
        if mtch:
            self._groupdict = mtch.groupdict()
            self._groups = mtch.groups()
        return mtch

    @property
    def base(self):
        return self._base
    
    @property
    def core(self):
        return self._core

    @property
    def full(self):
        return self._full

    @property
    def groupdict(self):
        return self._groupdict
        
    @property
    def groups(self):
        return self._groups

    @property
    def matches(self):
        return self._matches

    @property
    def name(self):
        return self._name
    


class Expander():
    "Variable expansion, tokenizers, etc.;"
    # VARPAT     = r'\s*?(\~{0,1}[\w\.\:]+)\s*?'

    def __init__(self, *dicts, **kwa):
        self._debug = kwa.get('debug', False)
        self._start = start = kwa.get('start', '{')
        self._end   = end = kwa.get('end', '}')
        self._namespaces = kwa.get('namespaces', None)
        self._helpers = dict(FIELDED = VarHelper('FIELDED', r'\~{0,1}(\w+)\.(\w+)', start=start, end=end),
                             DEEP = VarHelper('DEEP', r'\~{0,1}(\w+):(\w+)\.(\w+)', start=start, end=end),
                             SIMPLE = VarHelper('SIMPLE', r'\~{0,1}(\w+)', start=start, end=end),
                             NAMESPACED = VarHelper('NAMESPACED', r'\~{0,1}(\w+)\:(\w+)', start=start, end=end))
        if not self._namespaces:
            self.reset(*dicts)
        return

    def __getitem__(self, k):
        "Normal-scoping (innermost to outermost) reference by key"
        if self._namespaces:
            return self._getitem_ns(k)
        for dict_ in self._locals_first:
            if k in dict_:
                return dict_[k]
        raise KeyError(f"No such key {k} in any known scope")

    def __contains__(self, k):
        "Using same logic as getitem, search for the presence of the requested key;"
        if self._namespaces:
            return self._contains_namespaced(self, k)
        for dict_ in self._locals_first:
            if k in dict_:
                return True
        return False

    def __setitem__(self, k, v):
        "Set innermost (locals) key with value;"
        if self._namespaces:
            self._setitem_ns(k, v)
            return
        self.locals[k] = v

    # All the other expanding code goes here:
    def __call__(self, expr, **kwa) -> str:
        "Simple expander alias;"
        return self.expand(expr, **kwa)

    def _setitem_ns(self, k, v):
        where = "Expander._getitem_ns"
        if ('.' not in k) and (':' not in k):
            self._namespaces['default'][k] = v
        syntax_type, ns, var, field = self._validate_ns(k, getting=False)
        if syntax_type == 'simple':
            self._namespaces[ns][var] = v
        elif syntax_type in ['deep', 'fielded' ]:
            self._namespaces[ns][var][field] = v
        elif syntax_type == 'namespaced':
            self._namespaces[ns][var] = v
        else:
            raise IndexError(f"{where}: {k} didn't match any known pattern {syntax_type}")

    def _getitem_ns(self, k):
        where = "Expander._getitem_ns"
        if ('.' not in k) and (':' not in k):
            return self._namespaces['default'][k]
        val_tup = self._validate_ns(k)
        if val_tup[0] == False:
            raise IndexError(f"{where}: {k} invalid")
        value = val_tup[-1]
        return value

    def get(self, k, dflt = None) -> Any:
        "Same as __getitem__, but accepts a default value;"
        if self._namespaces:
            return self._get_ns(k, dflt)
        for dict_ in self._locals_first:
            if k in dict_:
                return dict_[k]
        return dflt

    def _get_ns(self, k, dflt = ""):
        "get with default, parses namespace syntax: name:var.field"
        where = "Expander.get_ns"
        val_tup = self._validate_ns(k)
        if val_tup[0] == False:
            return dflt
        return val_tup[-1]

    def _validate_ns(self, k, contains = False, getting=True):
        "Make sure the namespaced var syntax is valid;"
        def _contained(contains, exception, if_contained_value):
            "Raise an exception if contains == False, or return if_contained_value if k cannot be dereferenced;"
            if not contains:
                raise exception
            # do __contains__, indicated value for this state
            return if_contained_value

        where = "Expander._validate_ns"
        default_ns = self._namespaces['default']
        vhs = self._helpers             # Dict of VarHelpers
        deep, namespaced, fielded, simple = vhs['DEEP'], vhs['NAMESPACED'], vhs['FIELDED'], vhs['SIMPLE']
        falsy = ( False, False, False, False )
        setting = (not getting) and (not contains)
        getlen = k.startswith("~")
        # Initial deep match for namespace:varname.field
        if deep.match(k):
            core, ns, var, field = deep.groups
            if getting:
                if ns not in self._namespaces:
                    return _contained(contains, IndexError(f"{where}: Bad namespace {ns} in {k}"), False)
                dict_  = self._namespaces[ns]
                if var not in dict_:
                    return _contained(contains, IndexError(f"{where}: No such var {var} in {k}"), False)
                field_dict = dict_[var]
                if type(field_dict) != type(dict()):
                    return _contained(contains, IndexError(f"{where}: {k} does not have fields (dict)"), False)
                if field not in field_dict:
                    return _contained(contains, IndexError(f"{where}: {k} doesn't have a field {field}"), False)
                value = str(len(field_dict[field])) if getlen else str(field_dict[field])
                return 'deep', ns, var, field, value # Short circuit
            if setting:
                return 'deep', ns, var, field
            # getting == False, contains == True
            if ns not in self._namespaces:
                return falsy
            if var not in self._namespaces[ns]:
                return falsy
            if field not in self._namespaces[ns][var]:
                return falsy
            return deep, ns, var, field # final __contains__ state;

        if namespaced.match(k): # Match namespace:varname
            core, ns, var = namespaced.groups
            if getting:
                if ns not in self._namespaces:
                    return _contained(contains, IndexError(f"{where}: {k} references a non-existing namespace {ns}"), False)
                dict_ = self._namespaces[ns]
                if var not in dict_:
                    return _contained(contains, IndexError(f"{where}: {k} references a non-existing var {var}"), False)
            if setting:
                return 'namespaced', ns, var, None
            # Not getting, Not setting, just contains;
            if ns not in self._namespaces:
                return falsy
            dict_ = self._namespaces[ns]
            if var not in dict_:
                return falsy
            value = str(len(dict_[var])) if getlen else str(dict_[var])
            return 'namespaced', ns, var, value

        if fielded.match(k): # Match x.y in default namespace;
            ns = 'default'
            var, field = fielded.groups
            if getting:
                if var not in default_ns:
                    return _contained(contains, IndexError(f"{where}: {k} not in default namespace"))
                if type(default[var]) != type({}):
                    raise IndexError(f"{where}: {k} is not indexable to field")
                return 'fielded', ns, var, str(default_ns[var][field])
            if setting:
                return 'fielded', ns, var, field
            if var not in default_ns:
                return falsy
            if field not in default_ns[var]:
                return falsy
            value = str(len(default_ns[var][field])) if getlen else str(default_ns[var][field])
            return 'fielded', ns, var, value

        if simple.match(k):
            var = simple.groups[0]
            if getting:
                if var not in default_ns:
                    raise IndexError(f"{where}: {k} not in default namespace")
                value = str(len(default_ns[var])) if getlen else str(default_ns[var])
                return 'simple', 'default', k, value
            if setting:
                return 'simple', 'default', k, None
            if var not in default_ns:
                return _contained(contains, IndexError(f"{where}: {k} couldn't be parsed"), False)

        raise IndexError(f"{where}: Couldn't parse {k} as a variable name")

    def expand(self, text, **kwa):
        tokens = Expander.tokenize_static(text)
        olist = []
        for token in tokens:
            if not self.expandable(token):
                olist.append(token)
                continue
            # print(f"Expandable '{token}'")
            new_str = token
            while self.expandable(new_str):
                # print(f"expanding {new_str}")
                new_str = self.expand_token(token) # was: xp.expand_tokens(token)[0]
            olist.append(new_str)
        # print(f"olist: {olist}")
        ostr = " ".join(olist)
        # tokens = self.simple_tokenize(text, **kwa)
        # expanded_tokens = self.expand_tokens(*tokens)
        return ostr

    def expandable(self, token):
        if self._start in token:
            if self._end in token:
                if token.index(self._start) < token.index(self._end):
                    return True
        return False

    def _varlen(self, vn):
        # This needs to de-reference vn to vr, right?
        if type(vn) in [ type([]), type({}) ]:
            return str(len(vn))
        elif type(vn) in [ type("") ]:
            return str(len(Expander.tokenize(vn)))
        self._error = f"Can't process value of type {type(v)}"
        return False

    def _find_right_regex(self, token) -> VarHelper:
        result = dict(found=0, all=[ ], which={ })
        matchers = [ 'SIMPLE', 'NAMESPACED', 'FIELDED', 'DEEP' ] # Do not reorder;
        for xpndr_nm in matchers:
            vh = self._helpers[xpndr_nm] # This should be a VarHelper
            # print(f"Expander._find_right_regex: {str(vh)} : {token}")
            if not vh.match(token):
                continue
            if not vh.matches:
                continue
            # matcher = xpndr.helpers[xpndr_nm]
            result['found'] += len(vh['matches'])
            # found = xpndr.findall(token) # Now implement findall and replace? Or defer this to caller?
            result['all'] += vh['all']
            result['which'][xpndr.name] = vh['all']
            # print("Expander._find_right_regex: matched")
        # Now caller (expand_token) should do the suball against result;
        return result

    def expand_token(self, token, **kwa):
        subtokens = self._find_subtokens(token)
        if not subtokens:
            return token
        start, end = len(self._start), -len(self._end)
        new_token = token
        for full, core, *others in subtokens:
            if core.startswith("~"):
                v = str(len(self[core[1:]]))
            else:
                v = self.get(core, full) # Is this a good default (unexpanded) value?
            new_token = new_token.replace(full, v)
        return new_token

    def expand_tokens(self, *tokens, **kwa):
        expanded_tokens = [ ]
        default = kwa.get('default', "")
        for token in tokens:
            # print(f"expand_tokens: {token}")
            if not self.expandable(token):
                expanded_tokens.append(token)
                continue
            v = self.expand_token(token) # Expander.VARREX.match(token) # Expandable -- this better work;
            if v:
                expanded_tokens.append(v)
            else:
                if default:
                    expanded_tokens.append(default)
                    expanded_tokens.append(token)
                    continue
                ## bad_where, bad_ln = self._mf.trim_line_no, self._mf[self._mf.trim_line_no]
                self._error = f"Unset variable {varname}"
        return expanded_tokens

    def _find_subtokens(self, token: AnyStr) -> List:
        found = set()
        for helper in [ 'SIMPLE', 'NAMESPACED', 'FIELDED', 'DEEP' ]:
            vh = self._helpers[helper]
            helper_matches = vh.findall(token)
            if helper_matches:
                found = found.union(set(helper_matches))
        return list(found)

    def format(self, k):
        "Expansion Format support, ie: {foo:<format>}"
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
        "Explicit search for key from innermost to outermost;"
        ## dict_ = self._locals_first[0]
        try:
            v = self.mostest(k, self._locals_first)
        except KeyError as e:
            raise KeyError(f"No such key {k} from innermost scopes outward")
        return v

    def local_scope(self, k):
        "Explicitly only use local vars;"
        return self._locals_first[0][k]

    def mostest(self, k, which):
        "Search based on a provided list of dicts, in order;"
        for dict_ in which:
            if k in dict_:
                return dict_[k]
        raise KeyError(f"No such k {k} in any scope")

    def outermost(self, k):
        "Search for key in outermost dict only;"
        try:
            v = self.mostest(k, self._globals_first)
        except KeyError as e:
            raise KeyError(f"No such key {k} in from outermost scopes inward")
        return v

    def reset(self, *dicts):
        "reset -- use for scope change (ie: new locals at end of list);"
        self._globals_first = list(dicts)
        self._locals_first = self._globals_first[:]
        self._locals_first.reverse()
        return self._globals_first

    def simple_tokenize(self, txt, **kwa):
        "Use static tokenizer to break up a string;"
        tokens = Expander.tokenize(txt, **kwa)
        return tokens

    @staticmethod
    def rex_shlex(txt):
        "Static lexer to break basic expressions into tokens;"
        PATTERN = r"""( |[\"\'].*[\"\'])"""
        REX = re.compile(pattern)
        rl = list(filter(None, [t.strip() for t in rex.split(txt)]))
        return rl

    @staticmethod
    def tokenize_static(txt, **kwa):
        "The globally available tokenizer;"
        # splitter = Expander.rex_shlex
        splitter = shlex.split
        translation = kwa.get('translation', None)
        pattern = kwa.get('pattern', None)
        if pattern:
            rex = re.compile(pattern)
            splitter = rex.split
        tokens = splitter(txt)
        if translation:
            translated_tokens = [ ]
            for token in tokens:
                token.replace(translation[0], translation[1])
                translated_tokens.append(token)
        else:
            return tokens
        return translated_tokens

    def tokenize(self, txt, **kwa):
        "The instance-available tokenizer;"
        return Expander.tokenize_static(txt, **kwa)  # For now...

    @property
    def error(self):
        return self._error
    
    @property
    def globals(self):
        return self._globals_first[0]

    @property
    def helpers(self):
        return self._helpers

    @property
    def locals(self):
        return self._locals_first[0]

if __name__ == "__main__":
    "Test suite;"
    import sys

    def cli_get_args():
        pname, *args = sys.argv
        return args

    def test_continuation(continuation_fn):
        df = DynaFile(continuation_fn, continuation="\\", comment='//')
        results = [ ln for ln in df.trim_iter() ]
        return results

    def test_dynafile_include(include_fn):
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
        # print(ostr)
        return directives

    def test_dereferencer():
        globals_ = dict(ga="A", gb="B", gc="C", a="GA", b="BG", V="4:04")
        middles_ = dict(a="middle a", b="mid b", c="mid-c")
        locals_  = dict(a="a", b="b", c="c")
        xp = Expander(globals_, middles_, locals_)
        assert xp['a'] == "a"
        assert xp.innermost('a') == 'a'
        assert xp.outermost('a') == 'GA'
        assert xp['V'] == '4:04'
        # print(f"formatted V: {xp.format('V')}") # prior to shift to var%fmt ?

    def test_deref_ns():
        env = dict(os.environ)
        default = dict(a="def a", b="def b", c="def c")
        aux = dict(a="aux a", b="aux b", c="aux c", v1=1)
        fielded = dict(a=dict(thing_1 = "thing one", thing_2 = "thing_the_second"))
        xp = Expander(namespaces=dict(env=env, default=default, aux=aux, fielded=fielded))
        assert xp['env:USER'] == env['USER']
        assert xp['a'] == "def a"
        assert xp['aux:c'] == "aux c"
        assert xp['fielded:a.thing_2'] == "thing_the_second"
        assert xp['~fielded:a'] == "2"
        xp['fielded:a.thing_3'] = "3rd_of_things"
        assert xp['~fielded:a'] == "3"

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
            tokens = xp.tokenize(ln)
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
                # print(" ".join(olist))
                continue
            print(f"Unknown command {cmd} in {ln}")
            continue
        return True

    def test_expand_file_ns(src_fn):
        # >>> xp = Expander(global_dict, local_dict)
        #     s = xp("{foo}")
        #     s = xp("{foo}.{bar}")
        #     s = xp("{foo}.{frame:04d}.{ext}")
        # globals_, locals_ = dict(), dict()
        env, dflt = dict(os.environ), dict(first="1st", last="last", second="2nd", third="3rd")
        xp = Expander(start='{{', end='}}', namespaces = dict(env = env, default = dflt))
        directives = test_dynafile_include(src_fn)
        # Now we have every legit directive, and can ignore (already processed) includes;
        for ln in directives:
            tokens = Expander.tokenize(ln)
            cmd = tokens.pop(0).lower()
            if cmd == 'include':
                continue
            if cmd == 'var':
                k, v = tokens
                xp[k] = v
                continue
            if cmd == 'echo':
                olist = xp.expand_tokens(*tokens)
                print(" ".join(olist))
                continue
            print(f"Unknown command {cmd} in {ln}")
            continue
        return True

    def test_expander():
        fields = dict(x="Ecks", y="Why", z="Eh?", b="bee", c="see", third="3rd")
        x = dict(a=fields, b="Befoo", c="Sifu")
        env, dflt = dict(os.environ), dict(a="Ahey", b="bee", c="see", third="3rd")
        xp = Expander(namespaces=dict(env=env, default=dflt, x=x), start="{{", end="}}")
        s1 = "this is a string with {{x:a.z}}-{{b}}--{{~c}}: {{env:USER}}"
        tstr = "this is a string with Eh?-bee--3:"
        ostr = xp.expand(s1)
        # print(ostr)
        assert ostr.startswith(tstr)

    def test_tokenizer():
        s1 = "this is a string with {{x:a.z}}-{{b}}--{{c}}"
        tokens = Expander.tokenize_static(s1)
        assert len(tokens) == 6 # print(f"({len(tokens)}): {tokens}")

    def test_all(global_fn):
        # Test File Syntax:
        # global <varname> <stuff> -- add stuff to varname in global scope;
        # local <varname> <stuff> -- add stuff to varname in local scope;
        # include <filename> -- scan an included file at this point;
        # echo <stuff> -- echo stuff with expansions using default notation;
        test_expander()
        args = cli_get_args()
        include_fn = args.pop(0)
        print(f"test_dynafile_include({include_fn})")
        directives = test_dynafile_include(include_fn)
        print("test_tokenizer()")
        test_tokenizer()
        print("test_dereferencer()")
        test_dereferencer()
        print("test_deref_ns()")
        test_deref_ns()
        if 'ns' in include_fn:
            print(f"test_expand_file_ns({include_fn})")
            test_expand_file_ns(include_fn)
        else:
            print(f"test_expand_file({include_fn})")
            test_expand_file(include_fn)
        if not args:
            sys.exit(0)
        continuation_fn = args.pop(0)
        results = test_continuation(continuation_fn)
        print("test_continuation: \n".join(results))
        sys.exit(0)

    # Main
    test_all(None)
