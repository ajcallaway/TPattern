"""read_sofcoder: ingest a SOF-CODER / THEME DATANAME,T,Events file."""
from tpattern import read_sofcoder, Engine, Config

SAMPLE = (
    "DATANAME\tT\tEvents\n"
    "FCB-BETIS_FIRST\t1\t:\n"
    "FCB-BETIS_FIRST\t375\tCE,UD,IR,RA\n"
    "FCB-BETIS_FIRST\t650\tCE,UD,FT,RA\n"
    "FCB-BETIS_FIRST\t3775\tCE,C,MM\n"
    "FCB-BETIS_FIRST\t4000\t&\n"
    "RM-VALENCIA\t1\t:\n"
    "RM-VALENCIA\t500\tIZ,O,AR\n"
)


def _write(tmp_path, text, name="sof.csv"):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def test_sessions_and_explode(tmp_path):
    obs = read_sofcoder(_write(tmp_path, SAMPLE))
    assert [o.name for o in obs] == ["FCB-BETIS_FIRST", "RM-VALENCIA"]
    fcb = obs[0]
    # 3 event-rows exploded: 4 + 4 + 3 codes = 11 events (markers excluded)
    assert len(fcb.events) == 11
    # CE,UD,IR,RA all land at t=375 as co-timed events
    assert sorted(c for t, c in fcb.events if t == 375) == ["CE", "IR", "RA", "UD"]
    # no marker leaked into the events
    assert all(c not in (":", "&") for _, c in fcb.events)


def test_window_from_markers(tmp_path):
    # the : and & markers define the observation window (the NX/T denominator)
    obs = read_sofcoder(_write(tmp_path, SAMPLE))
    fcb = obs[0]
    assert (fcb.start, fcb.end) == (1, 4000)
    # a session without an & marker falls back to the last event
    rm = obs[1]
    assert rm.start == 1 and rm.end == 500


def test_whitespace_delimiter(tmp_path):
    text = "DATANAME T Events\nS1 1 :\nS1 100 A,B\nS1 200 A,C\nS1 300 &\n"
    obs = read_sofcoder(_write(tmp_path, text, "ws.csv"))
    assert obs[0].events == [(100, "A"), (100, "B"), (200, "A"), (200, "C")]
    assert (obs[0].start, obs[0].end) == (1, 300)


def test_frames_per_second_scaling(tmp_path):
    # frames -> ms: at 25 fps, frame 25 == 1000 ms
    text = "DATANAME T Events\nS1 25 A,B\nS1 50 A\n"
    obs = read_sofcoder(_write(tmp_path, text, "fps.csv"), frames_per_second=25)
    assert obs[0].events[0][0] == 1000


def test_flows_into_detection(tmp_path):
    obs = read_sofcoder(_write(tmp_path, SAMPLE))
    pats = Engine(obs, Config(min_lag=0)).detect()
    assert isinstance(pats, list)  # runs without error on SOF-CODER-sourced data


def test_positional_no_header(tmp_path):
    text = "S1 10 A,B\nS1 20 C\n"
    obs = read_sofcoder(_write(tmp_path, text, "noheader.csv"))
    assert obs[0].name == "S1" and len(obs[0].events) == 3
