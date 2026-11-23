"""The temperature watch that pauses a long run: it must act on a held temperature, not a spike."""
from jaxport.run_all import NO_READING_LIMIT_SECONDS, PAUSE_AT_C, RESUME_BELOW_C, SAMPLES_AVERAGED, Watch

POWER = 50.0


def watch_after(temperatures):
    watch = Watch()
    for temperature in temperatures:
        watch.add((temperature, POWER), watch.last_reading_at)
    return watch


def test_a_spike_does_not_pause_but_a_held_temperature_does():
    cool = PAUSE_AT_C - 15
    assert not watch_after([cool] * (SAMPLES_AVERAGED - 1) + [PAUSE_AT_C + 10]).too_hot()
    assert not watch_after([PAUSE_AT_C + 5] * (SAMPLES_AVERAGED - 1)).too_hot()  # too few readings to judge
    hot = watch_after([PAUSE_AT_C] * SAMPLES_AVERAGED)
    assert hot.too_hot() and hot.peak == PAUSE_AT_C and not hot.cool()


def test_resumes_only_once_the_card_has_cooled():
    assert not watch_after([PAUSE_AT_C, RESUME_BELOW_C]).cool()
    assert watch_after([PAUSE_AT_C, RESUME_BELOW_C - 1]).cool()
    assert not Watch().cool()  # no reading is not a cool reading


def test_missing_readings_count_as_blind_only_after_the_limit():
    watch = Watch()
    start = watch.last_reading_at
    watch.add(None, start + NO_READING_LIMIT_SECONDS - 1)
    assert not watch.blind(start + NO_READING_LIMIT_SECONDS - 1)
    assert watch.blind(start + NO_READING_LIMIT_SECONDS)
    watch.add((40.0, POWER), start + NO_READING_LIMIT_SECONDS)
    assert not watch.blind(start + NO_READING_LIMIT_SECONDS + 1)
