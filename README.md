# Docs2Types

Docs2types contains two utilities for increasing quality and type coverage of Python type stubs. Both utilities are highly experimental and PRs/suggestions are welcome.

1. `extract_and_apply_annotations`: semi-automated way to parse types from docstrings and apply them directly to stubs.
2. `extract_and_apply_defaults`: fully-automated way to extract parameter default values from functions and apply them directly to stubs.

This is similar to [docs2stubs](https://github.com/gramster/docs2stubs), but that tool generates stubs from the docs, while this tool applies additional types to existing stubs. In theory these two tools could work pretty well together, since the LLM should be able to infer more types (for example, in cases when the docstring isn't just a class name).

## extract_and_apply_annotations

This is a semi-automated way to add parameter defaults to stubs. It leverages LLMs in a way that 1. doesn't make the script super slow and 2. is deterministic across runs. Since the LLM is only used to generate a mapping of docstring types to type annotations, it should be a little bit easier to review.

### Example with pandas-stubs

1. clone [pandas-stubs](https://github.com/pandas-dev/pandas-stubs)
2. install pandas
3. `python3 extract_and_apply_annotations.py --show-types ./pandas-stubs/pandas-stubs pandas` to parse the stubs for missing parameter and return types, extract the relevant parts of the docstrings, and print all the snippets that were extracted
4. Give the snippets to your favorite LLM, and ask it to generate a dictionary literal of snippets to actual type annotation strings. If your stubs have an existing `.pyi` file for useful type aliases, you can include that with the context so the LLM can generate better types. Tell the LLM to give up and not generate a type if it can't tell what the type should be. You can look at the `type_map` variable for an example of the result.
5. Paste the generated dictionary literal into the script, replacing the value of the `type_map` variable.
6. Comment out any types that look fishy. If you want to be very conservative, you can comment out everything but the simple types like `int`/`str`/`bool`/`None`.
7. `python3 extract_and_apply_annotations.py ./pandas-stubs/pandas-stubs pandas` run the script again without the show-types flag to apply the types to the stubs. The script will look up the docstring snippets in the mapping you generated and apply the corresponding type annotation to the stub. If the entry is missing it will be skipped.


## extract_and_apply_defaults

This is a fully-automatic way to add parameter defaults to stubs. The first argument is the directory the stubs live in, and the second argument is the library to inspect at runtime.

While mypy's [stubgen](https://mypy.readthedocs.io/en/stable/stubgen.html) already inserts default values this wasn't always the case, so this can help fix up older stubs that have placeholder default values (like `x=...`). Having simple default values present the stubs can help improve the usefulness of the stubs for users.

### Example with pandas-stubs

1. clone [pandas-stubs](https://github.com/pandas-dev/pandas-stubs)
2. install pandas
3. `python3 extract_and_apply_defaults.py ./pandas-stubs/pandas-stubs pandas`

## Notes

- We skip any functions that are overloaded in the stubs, since docstrings usually do not give any indication of which overloads carry which types
- The tool generally cannot add `Self`-typed return annotations
- `extract_and_apply_defaults` can add default values that are incompatible with existing annotations in the stubs (for example, if the annotation isn't an optional type but the default at runtime is actually `None` - typically this means that we've found an issue with the annotation and we can fix it)
- Each type is looked at in isolation, so we can't infer anything fancy like generics, and based on experience many extracted generic types do not have type arguments