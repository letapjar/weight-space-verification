"""Write a trained network in the original experiment's two file formats: text and npz.

The original showed its networks to a language model as `<id>_actor.txt`: a line
giving the forward pass, then each layer's weights (one line per input row) and
biases, rounded to three decimals. `weights_text` reproduces that file exactly
for the original's own networks (tested), so ours can be read the same way.
`bare_weights_text` is the same numbers with every hint removed, for blind tests.

The original also published each network as `<id>.npz` (it trained in JAX, which
stores plain arrays): the actor and critic layers under the names below, with
each kernel shaped inputs x outputs. `save_npz` writes ours in that layout.
"""
import numpy as np
import torch.nn as nn

from original import ACTOR, ACTOR_LAYERS, CRITIC, CRITIC_LAYERS, NPZ_FILE  # noqa: F401

WEIGHTS_FILE = "weights.txt"
DECIMALS = 3


def linear_layers(policy):
    return [module for module in policy if isinstance(module, nn.Linear)]


def activation_name(policy) -> str:
    """The hidden activation as it is written in the forward pass, e.g. "tanh" or "relu"."""
    activation = next(module for module in policy if not isinstance(module, nn.Linear))
    return type(activation).__name__.lower()


def format_row(values) -> str:
    # + 0.0 turns -0.0 into 0.0 so tiny negatives don't print as "-0.000"
    return " ".join(f"{round(float(v), DECIMALS) + 0.0:.{DECIMALS}f}" for v in values)


def forward_pass_text(policy) -> str:
    activation, count = activation_name(policy), len(linear_layers(policy))
    hidden = [f"h{k} = {activation}({'x' if k == 1 else f'h{k - 1}'} @ W{k} + b{k})" for k in range(1, count)]
    return "; ".join(hidden + [f"logits = h{count - 1} @ W{count} + b{count}"])


def _layer_blocks(policy, weight_title, bias_title):
    """One text block per weight matrix and bias vector; the two callables write each block's title."""
    layers = linear_layers(policy)
    for k, layer in enumerate(layers, start=1):
        weight = layer.weight.detach().numpy().T  # row i = input i of this layer
        rows = [format_row(row) for row in weight]
        yield "\n".join([weight_title(k, len(layers), *weight.shape), *rows])
        yield "\n".join([bias_title(k, len(layers), weight.shape[1]), format_row(layer.bias.detach().numpy())])


def weights_text(policy) -> str:
    """The original experiment's layout: it names the network, its forward pass and its output layer."""
    def name(k, count):
        return "output layer" if k == count else f"layer {k}"

    def weight_title(k, count, n_in, n_out):
        row_note = f" (row i = input i), {n_out} values per line" if k == 1 else ""
        return f"W{k} ({name(k, count)} weights), shape {n_in} x {n_out}: one line per row{row_note}"

    def bias_title(k, count, n_out):
        return f"b{k} ({name(k, count)} biases), shape {n_out}:"

    header = (f"Policy network weights. Forward pass: {forward_pass_text(policy)}. "
              f"Values rounded to {DECIMALS} decimals.")
    return "\n\n".join([header, *_layer_blocks(policy, weight_title, bias_title)]) + "\n"


def bare_weights_text(policy) -> str:
    """Numbers and shapes only, for a blind reader.

    Unlike the original's layout, nothing says what kind of network this is,
    which activation it uses, or which layer is the output: the reader has to
    infer all of that from the weights.
    """
    def weight_title(k, count, n_in, n_out):
        return (f"W{k} (layer {k} weights), shape {n_in} x {n_out}: "
                f"one line per row (row i = input i), {n_out} values per line")

    def bias_title(k, count, n_out):
        return f"b{k} (layer {k} biases), shape {n_out}:"

    return "\n\n".join(_layer_blocks(policy, weight_title, bias_title)) + "\n"


def network_arrays(policy, critic=None) -> dict:
    """The network's arrays keyed as in the original's npz files; the critic is optional."""
    arrays = {}
    for prefix, network, names in ((ACTOR, policy, ACTOR_LAYERS), (CRITIC, critic, CRITIC_LAYERS)):
        if network is None:
            continue
        for layer, name in zip(linear_layers(network), names):
            arrays[f"{prefix}/{name}/kernel"] = layer.weight.detach().numpy().T.astype(np.float32)
            arrays[f"{prefix}/{name}/bias"] = layer.bias.detach().numpy().astype(np.float32)
    return arrays


def save_npz(path, policy, critic=None):
    np.savez(path, **network_arrays(policy, critic))
