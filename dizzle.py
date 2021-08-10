#!/bin/env python3
"""dizzle -- tools to build DSLs with;"""
if True:
    ## import os
    ## import pprint
    import re
    ## import sys
    ## import typing


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

    def insert_trimmed(self, newdata, where = None):
        if where == None:
            where = self.trim_line_no
        processed = self.trimmed[:where]
        unprocessed = self.trimmed[where:]
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

    # All the other expanding code goes here:
    def __call__(self, expr, **kwa):
        return self.expand(expr, **kwa)
        ## raise NotImplementedError

    def expand(self, text, **kwa):
        tokens = self.simple_tokenize(text, **kwa)
        expanded_tokens = self.expanded_tokens(*tokens)
        return expanded_tokens

    def expand_tokens(self, *tokens, **kwa):
        expanded_tokens = [ ]
        default = kwa.get('default')
        for token in tokens:
            # Replace with if (self._start in token) and (self._end in token)
            #   when we support re.sub for multi-expands per token;
            if token.startswith(self._start) and token.endswith(self._end):
                varname = token[1:-1]
                v = self._get(varname, None)
                if v != None:
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

    def innermost(self, k):
        dict_ = self._locals_first
        if k in dict_:
            return dict_[k]
        raise KeyError(f"No such key {k} in innermost scope")

    def outermost(self, k):
        dict_ = self._globals_first:
        if k in dict_:
            return dict_[k]
        raise KeyError(f"No such key {k} in outermost scope")

    def reset(self, *dicts):
        "reset -- use for scope change (ie: new locals at end of list);"
        self._globals_first = list(dicts)
        self._locals_first = self._globals_first[:]
        self._locals_first.reverse()

    def simple_tokenize(self, txt, **kwa):
        translation = kwa.get('translation', None)
        pattern = kwa.get('pattern', r'\s+')
        rex = re.compile(pattern)
        tokens = rex.split(txt)
        if translation:
            expanded_tokens = [ ]
            for token in tokens:
                token.replace(translation[0], translation[1])
                expanded_tokens.append(token)
            tokens = expanded_tokens
        return tokens

    @property
    def error(self):
        return self._error
    
if __name__ == "__main__":
    "Test suite;"
# >>> xp = Expander(global_dict, local_dict)
#     s = xp("{foo}")
#     s = xp("{foo}.{bar}")
#     s = xp("{foo}.{frame:04d}.{ext}")
