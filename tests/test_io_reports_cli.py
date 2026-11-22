import json
import numpy as np
import pandas as pd
import pytest
from biosignal_lab.cli import main
from biosignal_lab.io import read_csv
from biosignal_lab.pipeline import analyze
from biosignal_lab.report import html_report, json_report
from biosignal_lab.models import Recording, AnalysisConfig
from biosignal_lab.simulate import synthetic_recording


def test_csv_import_units_and_time(tmp_path):
    path=tmp_path/"a.csv"
    pd.DataFrame({"time_s":[i/100 for i in range(100)],"a":[.1]*100,"b":[.2]*100}).to_csv(path,index=False)
    rec=read_csv(path,sfreq=100,unit="mv",time_column="time_s")
    assert rec.data_uv[0,0]==pytest.approx(100)
    assert rec.channels==("a","b")


def test_csv_rejects_non_numeric(tmp_path):
    path=tmp_path/"bad.csv"
    pd.DataFrame({"channel":["oops"]*100}).to_csv(path,index=False)
    with pytest.raises(ValueError):
        read_csv(path,sfreq=200)


def test_csv_rejects_time_not_increasing(tmp_path):
    path=tmp_path/"time.csv"
    pd.DataFrame({"time": [0]*100, "a":range(100)}).to_csv(path,index=False)
    with pytest.raises(ValueError):
        read_csv(path,sfreq=100,time_column="time")


def test_csv_rejects_unknown_channels(tmp_path):
    path=tmp_path/"a.csv"
    pd.DataFrame({"a":range(100)}).to_csv(path,index=False)
    with pytest.raises(ValueError):
        read_csv(path,sfreq=100,channels=["missing"])


def test_html_report_escapes_filename():
    rec=Recording(np.ones((1,1000)),250,("test",),source="<script>alert(1)</script>")
    out=analyze(rec)
    report=html_report(out)
    assert "&lt;script&gt;" in report
    assert "<script>" not in report


def test_json_report_round_trip():
    out=analyze(synthetic_recording(duration_s=6,n_channels=1))
    report=json.loads(json_report(out))
    assert report["n_channels"]==1
    assert report["disclaimer"].startswith("Research")


def test_demo_cli_creates_csv(tmp_path):
    path=tmp_path/"demo.csv"
    assert main(["demo","--output",str(path),"--duration","10","--channels","2"])==0
    assert path.exists()
    assert list(pd.read_csv(path).columns)==["time_s","Ch1","Ch2"]


def test_cli_analysis_creates_artifacts(tmp_path):
    input_file=tmp_path/"demo.csv"
    main(["demo","--output",str(input_file),"--duration","10","--channels","2"])
    output=tmp_path/"result"
    assert main(["analyze","--input",str(input_file),"--output",str(output),
                 "--sfreq","250","--time-column","time_s"])==0
    assert (tmp_path/"result.json").exists()
    assert (tmp_path/"result.html").exists()
    assert (tmp_path/"result_quality.csv").exists()


def test_cli_requires_sfreq_for_csv(tmp_path):
    input_file=tmp_path/"demo.csv"
    main(["demo","--output",str(input_file),"--duration","5"])
    with pytest.raises(SystemExit):
        main(["analyze","--input",str(input_file)])
