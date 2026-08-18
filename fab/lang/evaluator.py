from collections.abc import Mapping, Sequence
from typing import override

from ..lang import astree
from .data import EvaluationContext, Function, List, Object, String
from .parser import parse
from ..model import Error


class EvaluationError(RuntimeError):
    context: EvaluationContext
    expr: astree.AstNode
    cause: Error

    def __init__(
        self,
        context: EvaluationContext,
        expr: astree.AstNode,
        cause: Error,
    ) -> None:
        self.context = context
        self.expr = expr
        self.cause = cause
        super().__init__(self.cause)


class NameError(Error):
    pass


class TypeError(Error):
    pass


def evaluate_context(context: EvaluationContext) -> Object:
    source = context.get_current_file().read_text()

    assignments = parse(source)

    class LoadedObject(Object):
        @override
        def has_attr(self, name: str) -> bool:
            return name in assignments

        @override
        async def get_attr(self, name: str) -> Object:
            expr = assignments[name]
            return await evaluate(expr, assignments, {}, context)

        @override
        def attrs(self) -> Sequence[str]:
            return list(assignments.keys())

    return LoadedObject()


async def evaluate(
    expr: astree.Expression,
    assignments: Mapping[str, astree.Expression],
    locals: Mapping[str, Object],
    context: EvaluationContext,
) -> Object:

    async def evaluate_variable(expr: astree.Variable) -> Object:
        var_name = expr.name.name
        if var_name in locals:
            return locals[var_name]
        if var_name in context.buildins:
            return context.buildins[var_name]
        if var_name not in assignments:
            raise EvaluationError(
                context, expr, NameError(f"Name '{var_name}' is not defined")
            )
        return await evaluate(assignments[var_name], assignments, locals, context)

    async def evaluate_literal_string(expr: astree.LiteralString) -> Object:
        return String(expr.value)

    async def evaluate_list(expr: astree.List) -> Object:
        evaluated_items = [
            await evaluate(item, assignments, locals, context) for item in expr.items
        ]
        return List(evaluated_items)

    async def evaluate_list_comprehension(expr: astree.ListComprehension) -> Object:

        items = await evaluate(expr.iterable, assignments, locals, context)
        assert isinstance(items, List)

        evaluated_items = [
            await evaluate(
                expr.expression, assignments, {expr.target.name: item}, context
            )
            for item in items.items
        ]

        return List(evaluated_items)

    async def evaluate_attribute_ref(expr: astree.AttributeRef) -> Object:
        evaluated_target = await evaluate(expr.target, assignments, locals, context)
        attr_name = expr.name.name
        if not evaluated_target.has_attr(attr_name):
            raise EvaluationError(
                context, expr, NameError(f"No attribute named '{attr_name}'")
            )
        return await evaluated_target.get_attr(attr_name)

    async def evaluate_call(expr: astree.Call) -> Object:
        evaluated_target = await evaluate(expr.target, assignments, locals, context)
        evaluated_args = [
            await evaluate(arg, assignments, locals, context) for arg in expr.pos_args
        ]
        evaluated_kwargs = {
            kw.name: await evaluate(arg, assignments, locals, context)
            for kw, arg in expr.key_args.items()
        }

        if not isinstance(evaluated_target, Function):
            raise EvaluationError(
                context, expr, TypeError("Target is not a a function")
            )

        try:
            return await evaluated_target.call(
                context, evaluated_args, evaluated_kwargs
            )
        except Error as e:
            raise EvaluationError(context, expr, e)

        except Exception as e:
            raise e

    if isinstance(expr, astree.Variable):
        return await evaluate_variable(expr)
    elif isinstance(expr, astree.LiteralString):
        return await evaluate_literal_string(expr)
    elif isinstance(expr, astree.List):
        return await evaluate_list(expr)
    elif isinstance(expr, astree.ListComprehension):
        return await evaluate_list_comprehension(expr)
    elif isinstance(expr, astree.AttributeRef):
        return await evaluate_attribute_ref(expr)
    elif isinstance(expr, astree.Call):
        return await evaluate_call(expr)
    else:
        raise NotImplementedError(f"Handling of {type(expr)} is not implemented")
