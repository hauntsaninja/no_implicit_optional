import argparse
import os
import re
import sys
from typing import Tuple

import libcst as cst
from libcst.codemod import (
    CodemodContext,
    TransformSuccess,
    VisitorBasedCodemodCommand,
    gather_files,
    parallel_exec_transform_with_prettyprint,
    transform_module,
)
from libcst.codemod.visitors import AddImportsVisitor


def is_typing_optional(expr: cst.BaseExpression) -> bool:
    if isinstance(expr, cst.Name):
        return expr.value == "Optional"
    if isinstance(expr, cst.Attribute):
        return (
            expr.attr.value == "Optional"
            and isinstance(expr.value, cst.Name)
            and expr.value.value in ("typing", "t", "T")
        )
    if isinstance(expr, cst.Subscript):
        return is_typing_optional(expr.value)
    return False


def is_typing_union_with_none(expr: cst.BaseExpression) -> bool:
    if isinstance(expr, cst.Subscript) and expr.slice:
        has_union_base = (isinstance(expr.value, cst.Name) and expr.value.value == "Union") or (
            isinstance(expr.value, cst.Attribute)
            and expr.value.attr.value == "Union"
            and isinstance(expr.value.value, cst.Name)
            and expr.value.value.value in ("typing", "t", "T")
        )
        if has_union_base:
            return any(
                isinstance(el.slice, cst.Index)
                and isinstance(el.slice.value, cst.Name)
                and el.slice.value.value == "None"
                for el in expr.slice
            )
    return False


def is_pep_604_union_with_none(expr: cst.BaseExpression) -> bool:
    if not isinstance(expr, cst.BinaryOperation) or not isinstance(expr.operator, cst.BitOr):
        return False
    return (
        (isinstance(expr.right, cst.Name) and expr.right.value == "None")
        or (isinstance(expr.left, cst.Name) and expr.left.value == "None")
        or (is_pep_604_union_with_none(expr.left) or is_pep_604_union_with_none(expr.right))
    )


def is_literal_with_none(expr: cst.BaseExpression) -> bool:
    if isinstance(expr, cst.Name) and expr.value == "None":
        return True
    if isinstance(expr, cst.Subscript) and expr.slice:
        has_literal_base = (isinstance(expr.value, cst.Name) and expr.value.value == "Literal") or (
            isinstance(expr.value, cst.Attribute)
            and expr.value.attr.value == "Literal"
            and isinstance(expr.value.value, cst.Name)
            and expr.value.value.value in ("typing", "t", "T")
        )
        if has_literal_base:
            return any(
                isinstance(el.slice, cst.Index)
                and isinstance(el.slice.value, cst.Name)
                and el.slice.value.value == "None"
                for el in expr.slice
            )
    return False


def is_optional_sounding_alias(expr: cst.BaseExpression) -> bool:
    return isinstance(expr, cst.Name) and bool(
        expr.value.endswith("Opt") or re.match(r"_?(Opt[A-Z]|Optional|None[A-Z])", expr.value)
    )


def is_typing_annotated(expr: cst.BaseExpression) -> bool:
    if isinstance(expr, cst.Name):
        return expr.value == "Annotated"
    if isinstance(expr, cst.Attribute):
        return (
            expr.attr.value == "Annotated"
            and isinstance(expr.value, cst.Name)
            and expr.value.value in ("typing", "t", "T")
        )
    if isinstance(expr, cst.Subscript):
        return is_typing_annotated(expr.value)
    return False


def type_hint_explicitly_allows_none_with_expr(
    expr: cst.BaseExpression,
) -> Tuple[bool, cst.BaseExpression]:
    if is_typing_annotated(expr):
        assert isinstance(expr, cst.Subscript)
        assert isinstance(expr.slice[0].slice, cst.Index)
        return type_hint_explicitly_allows_none_with_expr(expr.slice[0].slice.value)

    return (
        is_typing_optional(expr)
        or is_typing_union_with_none(expr)
        or is_pep_604_union_with_none(expr)
        or is_literal_with_none(expr)
        or is_optional_sounding_alias(expr)
    ), expr


def type_hint_explicitly_allows_none(expr: cst.BaseExpression) -> bool:
    allows_none, _ = type_hint_explicitly_allows_none_with_expr(expr)
    return allows_none


class NoImplicitOptionalCommand(VisitorBasedCodemodCommand):
    def leave_Param(self, original_node: cst.Param, updated_node: cst.Param) -> cst.Param:
        if (
            original_node.annotation is not None
            and original_node.default is not None
            and isinstance(original_node.default, cst.Name)
            and original_node.default.value == "None"
        ):
            top_level_expr = original_node.annotation.annotation

            allows_none, expr = type_hint_explicitly_allows_none_with_expr(top_level_expr)
            if not allows_none:
                new_expr: cst.BaseExpression = cst.Subscript(
                    value=cst.Name(value="Optional"),
                    slice=[cst.SubscriptElement(cst.Index(value=expr))],
                )
                if expr is not top_level_expr:  # happens with Annotated
                    new_expr = top_level_expr.deep_replace(expr, new_expr)

                new_annotation = cst.Annotation(new_expr)
                AddImportsVisitor.add_needed_import(self.context, "typing", "Optional")
                return updated_node.with_changes(annotation=new_annotation)

        return updated_node


def main() -> int:
    test()

    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()

    base = os.path.abspath(args.path)
    root = base if os.path.isdir(base) else os.path.dirname(base)
    files = gather_files([base], include_stubs=True)
    try:
        result = parallel_exec_transform_with_prettyprint(
            NoImplicitOptionalCommand(CodemodContext()), files, repo_root=root
        )
    except KeyboardInterrupt:
        print("Interrupted!", file=sys.stderr)
        return 2

    print(
        f"Finished codemodding {result.successes + result.skips + result.failures} files!",
        file=sys.stderr,
    )
    print(f" - Transformed {result.successes} files successfully.", file=sys.stderr)
    print(f" - Skipped {result.skips} files.", file=sys.stderr)
    print(f" - Failed to codemod {result.failures} files.", file=sys.stderr)
    print(f" - {result.warnings} warnings were generated.", file=sys.stderr)
    return 1 if result.failures > 0 else 0


def test() -> None:
    assert not type_hint_explicitly_allows_none(cst.parse_expression("int"))
    assert not type_hint_explicitly_allows_none(cst.parse_expression("str"))
    assert not type_hint_explicitly_allows_none(cst.parse_expression("List[str]"))
    assert not type_hint_explicitly_allows_none(cst.parse_expression("typing.Tuple[str]"))

    assert type_hint_explicitly_allows_none(cst.parse_expression("Optional"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("Optional[int]"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("t.Optional[int]"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("T.Optional[int]"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("typing.Optional[int]"))

    assert type_hint_explicitly_allows_none(cst.parse_expression("Union[None, int]"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("Union[int, None]"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("t.Union[int, None]"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("T.Union[int, None]"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("typing.Union[int, None]"))

    assert not type_hint_explicitly_allows_none(cst.parse_expression("Union"))
    assert not type_hint_explicitly_allows_none(cst.parse_expression("Union[int, str]"))
    assert not type_hint_explicitly_allows_none(cst.parse_expression("t.Union[int, str]"))
    assert not type_hint_explicitly_allows_none(cst.parse_expression("T.Union[int, str]"))
    assert not type_hint_explicitly_allows_none(cst.parse_expression("typing.Union[int, str]"))

    assert type_hint_explicitly_allows_none(cst.parse_expression("int | None"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("None | int"))
    assert type_hint_explicitly_allows_none(
        cst.parse_expression("int | str | None | float | bytes")
    )

    assert not type_hint_explicitly_allows_none(cst.parse_expression("int | str"))
    assert not type_hint_explicitly_allows_none(cst.parse_expression("int | str | float | bytes"))

    assert type_hint_explicitly_allows_none(cst.parse_expression("None"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("Literal[1, 2, None, 3]"))

    assert not type_hint_explicitly_allows_none(cst.parse_expression("Literal[1, 2]"))

    assert type_hint_explicitly_allows_none(cst.parse_expression("OptWhatever"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("_OptWhatever"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("WhateverOpt"))

    assert not type_hint_explicitly_allows_none(cst.parse_expression("Annotated[int, ...]"))
    assert type_hint_explicitly_allows_none(cst.parse_expression("Annotated[Optional[int], ...]"))
    assert type_hint_explicitly_allows_none(
        cst.parse_expression("typing.Annotated[Optional[int], ...]")
    )
    assert not type_hint_explicitly_allows_none(cst.parse_expression("t.Annotated[int, ...]"))

    cmd = NoImplicitOptionalCommand(CodemodContext())

    result = transform_module(cmd, "def foo(x: int = None): pass")
    assert isinstance(result, TransformSuccess)
    assert result.code == "from typing import Optional\n\ndef foo(x: Optional[int] = None): pass"

    result = transform_module(cmd, "def foo(x: list[int] = None): pass")
    assert isinstance(result, TransformSuccess)
    assert (
        result.code == "from typing import Optional\n\ndef foo(x: Optional[list[int]] = None): pass"
    )

    result = transform_module(cmd, "def foo(x: Annotated[int, str.isdigit] = None): pass")
    assert isinstance(result, TransformSuccess)
    assert (
        result.code
        == "from typing import Optional\n\ndef foo(x: Annotated[Optional[int], str.isdigit] = None): pass"
    )


if __name__ == "__main__":
    sys.exit(main())
