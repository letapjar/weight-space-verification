import json

import numpy as np

import heatmaps
from blind import ANSWER_KEY


def test_putting_a_reordered_network_back_gives_its_source_network():
    """For every rewired network of the matched set (turned 90, turned 180, scrambled): the first layer in the
    game's own order is the upright source's first layer, and in file order it is not."""
    key = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))
    upright = {network["source"]: blind_id for blind_id, network in key.items() if network["network"] == "actor"}
    checked = 0
    for blind_id, network in key.items():
        if network["network"] == "actor" and network["source"].startswith(
                ("runs_rewired_matched_", "runs_rewired_scrambled", "runs_rewired_inputs_shuffled")):
            source, rewired = heatmaps.first_layer(upright[network["derived_from"]]), heatmaps.first_layer(blind_id)
            assert np.array_equal(rewired[heatmaps.game_order(blind_id)], source)
            assert not np.array_equal(rewired, source)
            checked += 1
    assert checked == 47  # 12 turned 90, 11 turned 180 (the twelfth is in runs_rewired_180), 12 scrambled, 12 shuffled
