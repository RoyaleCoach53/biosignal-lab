"""Offline synthetic functional checks shared by isolated packages and containers."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

import numpy as np
import biosignal_lab
from biosignal_lab.cli import main
from biosignal_lab.engine import Signal, FilterSpec, filter_signal, resample_signal, welch_psd
from biosignal_lab.live import StreamInfo, SimulatedDevice, RingBuffer
from biosignal_lab.workspace import Workspace
from biosignal_lab.studio import Workflow, Node, Connection, Executor, builtin_registry
from biosignal_lab.studio.editor import frontend_available
from biosignal_lab.ai import evaluate_grouped, train_linear, save_linear_model, load_linear_model
from biosignal_lab.ai.demo import synthetic_feature_dataset


def core_checks():
    help_result=subprocess.run([str(Path(sys.executable).with_name('biosignal-lab')),'--help'],capture_output=True,text=True,check=True)
    assert 'demo' in help_result.stdout and 'analyze' in help_result.stdout
    assert frontend_available(), 'Studio canvas assets missing from installed package'
    import importlib.resources
    assets=importlib.resources.files('biosignal_lab.studio').joinpath('editor_frontend')
    assert all(assets.joinpath(name).is_file() for name in ('index.html','editor.js','editor.css'))
    timepoints=np.arange(2000)/250
    signal=Signal(np.sin(2*np.pi*10*timepoints)[None],250,('A',),unit='uV',reference='synthetic')
    filtered=filter_signal(signal,FilterSpec(cutoff=(1,40)))
    sampled=resample_signal(filtered,125)
    frequencies,power=welch_psd(sampled)
    assert sampled.sfreq==125 and frequencies[np.argmax(power[0])]==10
    info=StreamInfo(250,('A','B'),('uV','uV'),clock='simulated')
    device=SimulatedDevice(info)
    ring=RingBuffer(1000,2,250)
    try:
        block=device.read(100)
        ring.append(block)
        assert block.data.shape==(2,100)
    finally:device.close()
    graph=Workflow((Node('source','simulate',{'duration_s':4,'n_channels':2}),
                    Node('analysis','analyze',inputs={'signal':Connection('source')}),
                    Node('summary','summary',inputs={'analysis':Connection('analysis')})))
    result=Executor(builtin_registry()).execute(graph)
    assert result.outputs['summary']['out']['n_samples']==1000
    data=synthetic_feature_dataset(n_subjects=4,trials_per_subject=4)
    evaluation=evaluate_grouped(data,bootstrap_samples=100)
    assert all(not set(f['train_subjects'])&set(f['test_subjects']) for f in evaluation['folds'])
    with tempfile.TemporaryDirectory() as folder:
        folder=Path(folder)
        path=folder/'model.json'
        model=train_linear(data)
        save_linear_model(model,path)
        restored=load_linear_model(path)
        np.testing.assert_allclose(model.predict_proba(data.X),restored.predict_proba(data.X))
        source=folder/'demo.csv';base=folder/'report'
        assert main(['demo','--output',str(source),'--duration','4','--channels','2'])==0
        assert main(['analyze','--input',str(source),'--sfreq','250','--time-column','time_s','--output',str(base)])==0
        assert json.loads(base.with_suffix('.json').read_text())['n_channels']==2
        assert 'Research' in base.with_suffix('.html').read_text()
        store=Workspace(folder/'projects')
        project=store.create_project('Synthetic packaging check')
        revision=store.save(project,'settings',{'seed':42})
        assert Workspace(folder/'projects').load(project,'settings',revision)=={'seed':42}
    return {'version':biosignal_lab.__version__,'module_inside_prefix':Path(biosignal_lab.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()),'cli_installed_entrypoint':True,'frontend_assets':True,'engine_tone_and_resample':True,'live_simulation':True,'typed_workflow':True,'grouped_ai_and_safe_model':True,'cli_json_html':True,'project_recovery':True}


def container_checks():
    assert os.getuid()==10001
    from streamlit.testing.v1 import AppTest
    root=Path.cwd()
    app=AppTest.from_file(str(root/'platform_app.py'),default_timeout=90).run()
    assert not app.exception and not app.error
    for page in ('engine_app.py','live_app.py','ai_app.py','studio_app.py','workspace_app.py','app.py'):
        app.switch_page(page).run()
        assert not app.exception and not app.error,(page,[e.value for e in app.error])
    app.switch_page('live_app.py').run()
    next(b for b in app.button if b.label=='Capture synthetic stream').click().run()
    assert not app.exception and not app.error
    assert app.session_state['live_capture'][1].data.shape[1]==1250
    assert app.session_state['live_capture'][2].psd is not None
    app.switch_page('studio_app.py').run()
    next(b for b in app.button if b.label=='Run workflow').click().run()
    assert not app.exception and not app.error
    assert app.session_state['studio_result'].outputs['summary']['out']['n_samples']==2500
    app.switch_page('ai_app.py').run()
    next(s for s in app.slider if s.label=='Simulated subjects').set_value(4).run()
    next(b for b in app.button if b.label=='Run grouped evaluation').click().run()
    assert not app.exception and not app.error
    assert app.session_state['ai_report']['n_subjects']==4
    app.switch_page('workspace_app.py').run()
    next(t for t in app.text_input if t.label=='New project title').set_value('Container synthetic study')
    next(b for b in app.button if b.label=='Create project').click().run()
    assert not app.exception and not app.error
    next(t for t in app.text_area if t.label=='JSON document to save').set_value('{"seed":42}')
    next(b for b in app.button if b.label=='Save new revision').click().run()
    assert not app.exception and not app.error
    assert any('Saved revision' in s.value for s in app.success)
    app.run()
    assert not app.exception and not app.error
    assert '42' in app.json[0].value
    server=subprocess.Popen([sys.executable,'-m','streamlit','run',str(root/'platform_app.py'),'--server.headless=true','--server.address=127.0.0.1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for attempt in range(100):
            if server.poll() is not None:raise RuntimeError('Server failed before readiness')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health',timeout=1) as response:assert response.read()==b'ok'
                with urllib.request.urlopen('http://127.0.0.1:8501/',timeout=1) as response:assert b'<html' in response.read()
                break
            except OSError:time.sleep(.2)
        else:raise RuntimeError('Server readiness timed out')
    finally:
        server.terminate();server.wait(timeout=10)
    return {'uid':os.getuid(),'unified_navigation_pages':6,'studio_execution':True,'finite_live_capture':True,'ai_grouped_execution':True,'project_create_save_recover':True,'http_health_html':True,'network':'none'}


if __name__=='__main__':
    output=core_checks()
    if '--container' in sys.argv:output['container']=container_checks()
    assert output['module_inside_prefix']
    print('VERIFICATION_JSON='+json.dumps(output,sort_keys=True))
