"""MONAI Label adapter and task-to-output contract for future model bundles."""

TASK_OUTPUTS = {
    "couinaud": ("LiverAR_Couinaud", ("Segment_I", "Segment_II", "Segment_III", "Segment_IV", "Segment_V", "Segment_VI", "Segment_VII", "Segment_VIII")),
    "vessels": ("LiverAR_Vessels", ("PortalVein", "HepaticVeins", "LiverVessels")),
    "tumor": ("LiverAR_Tumor", ("Tumor",)),
}


def task_output_plan(task_key):
    try:
        return TASK_OUTPUTS[task_key]
    except KeyError:
        raise ValueError("Unknown segmentation task: {0}".format(task_key))


class MonaiLabelRunner:
    """Thin adapter around MONAI Label's documented Python client.

    A MONAI Bundle is selected by ``model_names``; this repository does not
    download or embed medical model weights.
    """

    def __init__(self, server_url, model_names=None, client_factory="auto"):
        self.server_url = server_url.rstrip("/")
        self.model_names = model_names or {}
        self.client = None
        self.available = False
        self.message = "MONAI Label client is not installed."
        if client_factory == "auto":
            try:
                from monailabel.client.client import MONAILabelClient
                client_factory = MONAILabelClient
            except ImportError:
                return
        if client_factory is not None:
            self.client = client_factory(self.server_url)
            self.available = True
            self.message = "MONAI Label client is available."

    def run_task(self, input_file, task_key, params=None):
        if not self.available:
            raise RuntimeError(self.message)
        model = self.model_names.get(task_key)
        if not model:
            raise RuntimeError("No MONAI Bundle model configured for task: {0}".format(task_key))
        response_file, response_body = self.client.infer(
            model=model,
            image_id="",
            params=params or {},
            file=input_file,
        )
        if not response_file:
            raise RuntimeError("MONAI Label returned no segmentation file for task: {0}".format(task_key))
        return response_file, response_body
