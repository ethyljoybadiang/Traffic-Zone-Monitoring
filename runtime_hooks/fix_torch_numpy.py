"""
PyInstaller runtime hook — fix for torch/_numpy/_ufuncs.py NameError.

torch/_numpy/_ufuncs.py generates functions via exec() inside a for-loop.
PyInstaller's frozen bytecode importer breaks the scoping so `name` is
undefined when the module body runs.

This hook pre-populates sys.modules with a complete stub (all actual names
extracted from torch._numpy._unary_ufuncs_impl and _binary_ufuncs_impl)
before that module is first imported.

YOLO detection does not call these numpy-compat ufuncs at runtime.
"""
import sys
import types


def _build_ufuncs_stub():
    mod = types.ModuleType("torch._numpy._ufuncs")

    # Complete list from dir(torch._numpy._unary_ufuncs_impl)
    _UNARY = [
        "abs", "absolute", "arccos", "arccosh", "arcsin", "arcsinh",
        "arctan", "arctanh", "bitwise_not", "cbrt", "ceil", "conj",
        "conjugate", "cos", "cosh", "deg2rad", "degrees", "exp", "exp2",
        "expm1", "fabs", "fix", "floor", "invert", "isfinite", "isinf",
        "isnan", "log", "log10", "log1p", "log2", "logical_not",
        "negative", "positive", "rad2deg", "radians", "reciprocal", "rint",
        "sign", "signbit", "sin", "sinh", "sqrt", "square", "tan", "tanh",
        "trunc",
    ]

    # Complete list from dir(torch._numpy._binary_ufuncs_impl) + extras
    _BINARY = [
        "add", "arctan2", "bitwise_and", "bitwise_or", "bitwise_xor",
        "copysign", "divide", "divmod", "equal", "float_power",
        "floor_divide", "fmax", "fmin", "fmod", "gcd", "greater",
        "greater_equal", "heaviside", "hypot", "lcm", "ldexp",
        "left_shift", "less", "less_equal", "logaddexp", "logaddexp2",
        "logical_and", "logical_or", "logical_xor", "matmul", "maximum",
        "minimum", "modf", "multiply", "nextafter", "not_equal", "power",
        "remainder", "right_shift", "subtract", "true_divide",
    ]

    def _make_fn(name):
        def _fn(*args, **kwargs):
            raise NotImplementedError(
                f"torch._numpy._ufuncs.{name} stub called "
                f"(PyInstaller build — this should not happen during YOLO inference)"
            )
        _fn.__name__ = name
        return _fn

    for n in _UNARY + _BINARY:
        setattr(mod, n, _make_fn(n))

    return mod


# Register BEFORE any torch import can trigger the broken importer
if "torch._numpy._ufuncs" not in sys.modules:
    sys.modules["torch._numpy._ufuncs"] = _build_ufuncs_stub()
