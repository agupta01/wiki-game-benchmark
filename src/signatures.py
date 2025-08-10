from dspy import ChainOfThought, InputField, OutputField, Predict, Refine, Signature

from src.models import StepInput, StepOutput


class Step(Signature):
    input: StepInput = InputField()
    output: StepOutput = OutputField()


def valid_link(args, pred) -> float:
    return 1.0 if pred.output.selected_link in args["input"].current_page.links else 0.0


get_next_page = Refine(
    module=Predict(Step),
    N=3,
    reward_fn=valid_link,
    threshold=1.0,
)
get_next_page_chain = Refine(
    module=ChainOfThought(Step),
    N=3,
    reward_fn=valid_link,
    threshold=1.0,
)
