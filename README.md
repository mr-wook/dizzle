# dizzle
Tools for building Domain-Specific-Languages (DSLs)

## DynaFile
the DynaFile class is used to support threading multiple files together, as well as comment and blank line trimming,
and an iterator that keeps track of the current location even after other files (include/import/etc.) are inserted in the middle.

## Expander
The Expander class supports multiple source dictionaries (global to most local, or namespaces) to support scoped variable lookups for variables that
are provided using a well-known (default, and declared variants) syntax.

### namespaced syntax
```
xp = Expander(namespaces=dict(default=dict(a=1, b=2, c=3, z=dict(name="z", value="26")),
                              fielded=dict(a=dict(a=11, b=22, c=33)), env=os.environ))
d = xp['c'] + 1
xp['d'] = d
print(f"{xp['fielded':a.b']}")
print(f"User: {xp['env:USER']}")
xp['z.meta'] = 'last'
```

### scoped syntax
```
xp = Expander()   # Creates globals (outermost) and locals (innermost) by default and searches for matches from inner to outer
```


