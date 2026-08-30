"""Runtime discovery adapter for installed SlicerTotalSegmentator variants."""

from dataclasses import dataclass
import inspect


@dataclass
class DependencyReport:
    available: bool
    message: str
    callable_methods: tuple = ()
    logic: object = None


class TotalSegmentatorRunner:
    TASKS = {"couinaud": "liver_segments", "vessels": "liver_vessels", "tumor": "liver_lesions"}

    def __init__(self, slicer_module):
        self.slicer = slicer_module
        self.report = self.validate_dependencies(slicer_module)

    @staticmethod
    def validate_dependencies(slicer_module):
        if slicer_module is None:
            return DependencyReport(False, "3D Slicer is not available in this Python runtime.")
        candidates = ("TotalSegmentator", "totalSegmentator", "totalsegmentator")
        for name in candidates:
            try:
                logic = slicer_module.util.getModuleLogic(name)
            except Exception:
                continue
            if logic:
                methods = tuple(sorted(name for name in dir(logic) if callable(getattr(logic, name, None)) and not name.startswith("_")))
                return DependencyReport(True, "TotalSegmentator logic discovered.", methods, logic)
        return DependencyReport(
            False,
            "Install and enable SlicerTotalSegmentator, then restart 3D Slicer. Its module logic could not be found.",
        )

    def run_task(self, input_volume, task_key, output_segmentation=None):
        if not self.report.available:
            raise RuntimeError(self.report.message)
        task_name = self.TASKS[task_key]
        process = getattr(self.report.logic, "process", None)
        if callable(process):
            # Keep peak host-RAM use predictable on laptops. These options are
            # filtered below for older SlicerTotalSegmentator versions.
            options = {"task": task_name, "interactive": False, "fast": True, "nr_threads": 1}
            try:
                parameters = inspect.signature(process).parameters
                accepts_kwargs = any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values())
                if not accepts_kwargs:
                    options = {key: value for key, value in options.items() if key in parameters}
            except (TypeError, ValueError):
                pass
            return process(input_volume, output_segmentation, **options)
        candidates = ("run", "process", "apply", "runSegmentation", "runTotalSegmentator")
        attempted = []
        for method_name in candidates:
            method = getattr(self.report.logic, method_name, None)
            if not callable(method):
                continue
            attempted.append(method_name)
            for args in ((input_volume, output_segmentation, task_name), (input_volume, output_segmentation), (input_volume,)):
                try:
                    return method(*args)
                except TypeError:
                    continue
        available = ", ".join(self.report.callable_methods[:20]) or "none"
        raise RuntimeError(
            "The installed TotalSegmentator logic does not expose a supported callable entry point. "
            "Available methods: {0}. Tried: {1}.".format(available, ", ".join(attempted) or "none")
        )
