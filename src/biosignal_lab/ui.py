"""Small dashboard compatibility helpers; no signal-processing changes."""
import inspect


def display_options(renderer, description):
    """Use current stretch/alt APIs when advertised, retaining older Streamlit support."""
    parameters = inspect.signature(renderer).parameters
    width = parameters.get("width")
    options = {"width": "stretch"} if width is not None and width.default == "stretch" else {"use_container_width": True}
    if "alt" in parameters:
        options["alt"] = description
    return options
