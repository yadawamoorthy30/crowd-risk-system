from types import SimpleNamespace

from app.services.vision.flow import (
    TripwireCounter, TripwireLine, signed_distance,
)

W, H = 1000, 500   # frame size; the line below is y=250 px, x=100..900 px


def make(in_side="RIGHT", cooldown=3.0, forget_after=30):
    line = TripwireLine(0.1, 0.5, 0.9, 0.5, in_side=in_side, cooldown_sec=cooldown)
    return TripwireCounter(line, forget_after=forget_after)


def run(counter, points, track_id=1):
    for t, x, y in points:
        counter.update([SimpleNamespace(track_id=track_id, foot_x=x, foot_y=y)], W, H, t)


DOWN = [(0.0, 500, 200), (0.1, 500, 230), (0.2, 500, 270), (0.3, 500, 300)]
UP = [(0.0, 500, 300), (0.1, 500, 270), (0.2, 500, 230), (0.3, 500, 200)]


def test_distance_sign_below_is_right():
    assert signed_distance(500, 300, 100, 250, 900, 250) == 50
    assert signed_distance(500, 200, 100, 250, 900, 250) == -50


def test_in_crossing_and_event_has_no_track_id():
    c = make()
    run(c, DOWN)
    assert (c.in_total, c.out_total) == (1, 0)
    assert c.events[0].direction == "IN"
    assert not hasattr(c.events[0], "track_id")


def test_out_crossing():
    c = make()
    run(c, UP)
    assert (c.in_total, c.out_total) == (0, 1)


def test_no_crossing():
    c = make()
    run(c, [(0.0, 500, 200), (0.1, 520, 190), (0.2, 540, 180)])
    assert (c.in_total, c.out_total) == (0, 0)


def test_jitter_inside_band_is_ignored():
    c = make()
    run(c, [(0.0, 500, 200)] + [(0.1 * i, 500, y) for i, y in
                               enumerate([245, 255, 248, 252, 246], start=1)])
    assert (c.in_total, c.out_total) == (0, 0)


def test_flicker_within_cooldown_counts_once():
    c = make()
    run(c, [(0.0, 500, 200), (0.5, 500, 300), (1.0, 500, 220), (1.5, 500, 300)])
    assert (c.in_total, c.out_total) == (1, 0)


def test_track_that_appears_past_the_line_is_not_counted():
    c = make()
    run(c, [(0.0, 500, 300), (0.1, 500, 320), (0.2, 500, 400)])
    assert (c.in_total, c.out_total) == (0, 0)


def test_walking_around_the_end_of_the_line_is_not_counted():
    c = make()
    run(c, [(0.0, 950, 200), (0.1, 950, 300)])   # x=950 is beyond the segment end (900)
    assert (c.in_total, c.out_total) == (0, 0)


def test_left_in_side_flips_direction():
    c = make(in_side="LEFT")
    run(c, DOWN)
    assert (c.in_total, c.out_total) == (0, 1)


def test_return_after_cooldown_counts_out():
    c = make()
    run(c, DOWN)
    run(c, [(5.0, 500, 200)])
    assert (c.in_total, c.out_total) == (1, 1)


def test_quick_return_is_counted_after_cooldown_ends():
    c = make()
    run(c, DOWN)                       # IN at t=0.2
    run(c, [(1.0, 500, 200)])          # back on the other side, inside cooldown
    assert c.out_total == 0
    run(c, [(4.0, 500, 200)])          # cooldown over, still on that side
    assert (c.in_total, c.out_total) == (1, 1)


def test_two_tracks_are_independent():
    c = make()
    frames = [
        (0.0, 500, 200, 600, 300), (0.1, 500, 230, 600, 270),
        (0.2, 500, 270, 600, 230), (0.3, 500, 300, 600, 200),
    ]
    for t, x1, y1, x2, y2 in frames:
        c.update([SimpleNamespace(track_id=1, foot_x=x1, foot_y=y1),
                  SimpleNamespace(track_id=2, foot_x=x2, foot_y=y2)], W, H, t)
    assert (c.in_total, c.out_total) == (1, 1)


def test_old_tracks_are_forgotten():
    c = make(forget_after=2)
    run(c, [(0.0, 500, 200)])
    assert c.tracked_count == 1
    for t in (0.1, 0.2, 0.3):
        c.update([], W, H, t)
    assert c.tracked_count == 0