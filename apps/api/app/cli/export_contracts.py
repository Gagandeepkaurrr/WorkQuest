import json
from pathlib import Path
from app.main import app
from app.engine.types import Scenario
root=Path(__file__).resolve().parents[4]
folder=root/'packages/contracts'
folder.mkdir(parents=True,exist_ok=True)
(folder/'openapi.json').write_text(json.dumps(app.openapi(),indent=2,sort_keys=True)+'\n')
(folder/'scenario.schema.json').write_text(json.dumps(Scenario.model_json_schema(),indent=2,sort_keys=True)+'\n')
print('Exported OpenAPI and private scenario schema.')
