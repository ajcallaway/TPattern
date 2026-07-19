"""Regenerate the offline (self-contained) Colab notebook by bundling the current
package source into it. Run after changing the package:  python colab/build_offline_notebook.py"""
import json, base64, gzip
from pathlib import Path
root = Path(__file__).resolve().parents[1]
pkg = {f.name: f.read_text() for f in sorted((root/"tpattern").glob("*.py"))}
payload = base64.b64encode(gzip.compress(json.dumps(pkg).encode())).decode()
setup = ('#@title Set up tpattern — run once (code hidden) { display-mode: "form" }\n'
 "# ----------------------------------------------------------------------------\n"
 "# NOTE FOR THE CURIOUS READER\n"
 "# The tpattern source is bundled (gzipped + base64) into this one cell purely so\n"
 "# the notebook is self-contained and runs in Google Colab with nothing to\n"
 "# install or download. It is hidden only for convenience — nothing here is\n"
 "# closed. The full, readable, commented Python source is openly available:\n"
 "#   archive (permanent DOI): https://doi.org/10.5281/zenodo.21397543\n"
 "#   source repository:       https://github.com/ajcallaway/TPattern\n"
 "# The cell below simply unpacks that same source to a local 'tpattern/' folder.\n"
 "# ----------------------------------------------------------------------------\n"
 "import base64, gzip, json, os\n"
 "FILES = json.loads(gzip.decompress(base64.b64decode('''" + payload + "''')).decode())\n"
 "os.makedirs('tpattern', exist_ok=True)\n"
 "for name, src in FILES.items(): open('tpattern/'+name, 'w').write(src)\n"
 "print('tpattern ready:', len(FILES), 'modules')")
nb={"cells":[
 {"cell_type":"markdown","metadata":{},"source":["# tpattern — guided analysis (offline / no-install)\n\n","Same guided analysis as the main notebook, but the package is **bundled inside** — no install from GitHub. Run the cells in order; the setup cell is collapsed. Upload your CSV, *Inspect*, review the settings, *Run*.\n\n","*(This copy bundles a snapshot of the code; for the latest version use `tpattern_guided_analysis.ipynb`.)*"]},
 {"cell_type":"code","execution_count":None,"metadata":{},"outputs":[],"source":["#@title Dependencies — run once { display-mode: \"form\" }\n!pip install -q numpy scipy matplotlib ipywidgets pandas openpyxl"]},
 {"cell_type":"code","execution_count":None,"metadata":{"cellView":"form"},"outputs":[],"source":[setup]},
 {"cell_type":"code","execution_count":None,"metadata":{},"outputs":[],"source":["from tpattern import launch\nlaunch()"]}],
 "metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"colab":{"provenance":[]}},"nbformat":4,"nbformat_minor":5}
out=root/"colab"/"tpattern_guided_analysis_offline.ipynb"; out.write_text(json.dumps(nb,indent=1))
print(f"wrote {out.name} ({out.stat().st_size/1024:.0f} KB)")
