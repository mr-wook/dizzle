# dizzle
Tools for building Domain-Specific-Languages (DSLs)

## DynaFile
the DynaFile class is used to support threading multiple files together, as well as comment and blank line trimming,
and an iterator that keeps track of the current location even after other files (include/import/etc.) are inserted in the middle.

## Expander
The Expander class supports multiple source dictionaries (global to most local) to support scoped variable lookups for variables that
are provided using a well-known (default, and declared variants) syntax.

