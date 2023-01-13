#!/bin/env python3

if True:
    import os
    import re


class Fixer:
    def __init__(self, start = None, end = None, unsafe=False, **vars):
        self._vars = { **vars, **self._load() }
        self._unsafe = unsafe   # This risks eval-injections;
        if start == None:
            start = "{"
        if end == None:
            end = "}"
        self._start, self._end = start, end
        pat = rf"(?P<full>{start}(?P<var>\w+){end})"
        self._rex = re.compile(pat)
        expr_pat = rf"(?P<full>{start}(?P<words>.*?){end})"
        self._expr_rex = re.compile(expr_pat)

    def __getitem__(self, k):
        return self._vars[k]

    def __contains__(self, k):
        return k in self._vars

    def __call__(self, s):
        self._source = s
        if not self._has_stuff(s):
            self._dest = None
            return s
        tups = self._rex.findall(s)
        for tup in tups:
            full, k = tup
            s = s.replace(full, self[k])
        if not self._has_stuff(s):
            self._dest = s
            return s

        # Expression support
        tups = self._expr_rex.findall(s)
        for tup in tups:
            full, words = tup
            particles = [ ]
            for word in re.split(r'\s+', words):
                if word in self:
                    particles.append(self[word])
                else:
                    particles.append(word)
            departicled = " ".join(particles)
            if self._unsafe:
                departicled = str(eval(departicled))
            s = s.replace(full, departicled)
        self._dest = s
        return s

    def _has_stuff(self, s):
        if self._start not in s:
            return False
        if self._end not in s:
            return False
        if s.index(self._start) > s.index(self._end):
            raise ValueError(f"Malformed string: {s}")
            return False
        return True

    def _load(self, fn = ".vars"):
        if not os.path.isfile(fn):
            return dict()
        with open(fn, 'r') as ifd:
            ibuf = [ln.strip() for ln in ifd.readlines()]
            tupdict = dict([re.split(r'\s+', ln, 1) for ln in ibuf])
        return tupdict

    @property
    def dest(self):
        return self._dest
    
    @property
    def vars(self):
        return self._vars
    
    @property
    def source(self):
        return self._source


if __name__ == "__main__":
    from   pprint import pprint
    import sys


   def main(args):
        start, end = "{{", "}}"
        if len(args) == 1:
            s = args.pop(0)
        elif len(args) == 3:
            start = args.pop(0)
            end = args.pop(0)
            s = args.pop(0)
        elif len(args) == 0:
            s = "{{a}}-{{b}}-({{example_3rd_term}}) is a simple test string;"
        else:
            print("Yeah, don't really understand that...")
            sys.exit(1)

        vars = dict(a="apple", b="banana", example_3rd_term="thrice", d="dolt", e="EasyIce")
        fixer = Fixer(start, end, unsafe=True)
        fixed = fixer(s)
        print(f"{fixer.source} --> {fixer.dest}")
        print(fixer.vars)

    # If we make the var term more liberal (via |) can we parse words out of var,
    # and if they are not in vars simply leave them un-replaced;

    def test_master(args):
        # These tests all rely on ./.vars having the right fields defined;
        tests = [ dict(name='baseline',
                       s="{a}-{b}-({example_3rd_term}) is a simple test string;"),
                  dict(name='evaluated', unsafe=True,
                       s = "{a}-{b}-({x1 / x2}) is a simple test string;" ),
                  dict(name='repetitive',
                       s = "{a} {b} {a} {c} {a} {b} -- produced by Phil Collins;") ]
        for test in tests:
            fixer = Fixer(unsafe = test.get('unsafe', False))
            fixed = fixer(test['s'])
            print(f"{fixer.source} --> {fixer.dest}")

    pname, *args = sys.argv[:]
    if args and args[0].lower() == 'test':
        test_master(args)
    else:
        main(args)
    sys.exit(0)
