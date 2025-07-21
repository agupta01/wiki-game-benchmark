from dspy import Predict
from models import StepInput, StepOutput # pyright: ignore[reportMissingImports]

get_next_page = Predict("input: StepInput -> output: StepOutput")
