from collections.abc import Mapping, Sequence
import traceback
from typing import override

from ..lang import astree
from .data import EvaluationContext, Function, FunctionCallError, List, Object, String
from .parser import parse


class EvaluationError(RuntimeError):
    context: EvaluationContext
    expr: astree.AstNode
    msg: str

    def __init__(
        self, context: EvaluationContext, expr: astree.AstNode, msg: str
    ) -> None:
        self.context = context
        self.expr = expr
        self.msg = msg
        super().__init__(msg)

    @override
    def __str__(self) -> str:
        return f"{self.msg}: {str(self.expr)}"


class FunctionEvaluationError(EvaluationError):
    def __init__(
        self, context: EvaluationContext, expr: astree.AstNode, reason: str
    ) -> None:
        super().__init__(context, expr, reason)


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
            raise EvaluationError(context, expr, f"Name '{var_name}' is not defined")
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
            raise EvaluationError(context, expr, f"No attribute named '{attr_name}'")
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
            raise EvaluationError(context, expr, "Target is not a callable")

        try:
            return await evaluated_target.call(
                context, evaluated_args, evaluated_kwargs
            )
        except FunctionCallError as e:
            raise FunctionEvaluationError(context, expr, str(e)) from None

        except Exception as e:
            raise FunctionEvaluationError(
                context,
                expr,
                "Internal error: " + str(traceback.format_exc()),

            ) from None

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
