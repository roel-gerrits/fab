from collections.abc import Mapping, Sequence
from typing import override

from ..lang import astree
from .data import EvaluationContext, Function, List, Object, String
from .parser import parse


class EvaluationError(RuntimeError):
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
            return await evaluate(expr, assignments, context)

        @override
        def attrs(self) -> Sequence[str]:
            return list(assignments.keys())

    return LoadedObject()


async def evaluate(
    expr: astree.Expression,
    assignments: Mapping[str, astree.Expression],
    context: EvaluationContext,
) -> Object:

    async def evaluate_variable(expr: astree.Variable) -> Object:
        var_name = expr.name.name
        if var_name in context.buildins:
            return context.buildins[var_name]
        if var_name not in assignments:
            raise EvaluationError(f"No variable named '{var_name}'")
        return await evaluate(assignments[var_name], assignments, context)

    async def evaluate_literal_string(expr: astree.LiteralString) -> Object:
        return String(expr.value)

    async def evaluate_list(expr: astree.List) -> Object:
        evaluated_items = [
            await evaluate(item, assignments, context) for item in expr.items
        ]
        return List(evaluated_items)

    async def evaluate_attribute_ref(expr: astree.AttributeRef) -> Object:
        evaluated_target = await evaluate(expr.target, assignments, context)
        attr_name = expr.name.name
        if not evaluated_target.has_attr(attr_name):
            raise EvaluationError(f"No attribute named '{attr_name}'")
        return await evaluated_target.get_attr(attr_name)

    async def evaluate_call(expr: astree.Call) -> Object:
        evaluated_target = await evaluate(expr.target, assignments, context)
        evaluated_args = [
            await evaluate(arg, assignments, context) for arg in expr.pos_args
        ]
        evaluated_kwargs = {
            kw.name: await evaluate(arg, assignments, context)
            for kw, arg in expr.key_args.items()
        }

        if isinstance(evaluated_target, Function):
            return await evaluate_function_call(
                evaluated_target, evaluated_args, evaluated_kwargs
            )
        else:
            raise EvaluationError("Target is not a callable")

    async def evaluate_function_call(
        target: Function,
        args: list[Object],
        kwargs: dict[str, Object],
    ) -> Object:
        return await target.call(context, args, kwargs)

    if isinstance(expr, astree.Variable):
        return await evaluate_variable(expr)
    elif isinstance(expr, astree.LiteralString):
        return await evaluate_literal_string(expr)
    elif isinstance(expr, astree.List):
        return await evaluate_list(expr)
    elif isinstance(expr, astree.AttributeRef):
        return await evaluate_attribute_ref(expr)
    elif isinstance(expr, astree.Call):
        return await evaluate_call(expr)
    else:
        raise NotImplementedError
